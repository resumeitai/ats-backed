import csv
import io
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg, Count, Sum, Q, F, Value, CharField, IntegerField,
    Case, When,
)
from django.db.models.functions import (
    ExtractHour, ExtractWeekDay, TruncMonth,
)
from django.utils import timezone

from ats_checker.models import ATSScore, KeywordMatch, OptimizationSuggestion
from resumes.models import Resume
from subscriptions.models import Subscription, SubscriptionPlan, Transaction
from templates.models import Template
from users.models import UserActivity, Referral

User = get_user_model()


class AnalyticsService:
    """
    Service class that encapsulates all analytics computation logic.
    All methods are static so they can be called without instantiation.
    """

    @staticmethod
    def get_dashboard_stats():
        """
        Return high-level dashboard statistics.

        - total_users: count of all non-deleted users
        - premium_users: users with an active subscription whose end_date
          has not passed
        - weekly_signups: users created in the last 7 days
        - avg_ats_score: average ATS score across all analyses
        - total_referrals: total referral records
        - successful_referrals: referrals where is_successful is True
        """
        now = timezone.now()
        seven_days_ago = now - timezone.timedelta(days=7)
        today = now.date()

        total_users = User.objects.filter(is_deleted=False).count()

        premium_users = User.objects.filter(
            is_deleted=False,
            subscriptions__status='active',
            subscriptions__end_date__gte=today,
        ).distinct().count()

        weekly_signups = User.objects.filter(
            is_deleted=False,
            created_at__gte=seven_days_ago,
        ).count()

        avg_ats_score = ATSScore.objects.aggregate(
            avg_score=Avg('score')
        )['avg_score']

        total_referrals = Referral.objects.count()
        successful_referrals = Referral.objects.filter(is_successful=True).count()

        return {
            'total_users': total_users,
            'premium_users': premium_users,
            'weekly_signups': weekly_signups,
            'avg_ats_score': round(avg_ats_score, 2) if avg_ats_score else 0,
            'total_referrals': total_referrals,
            'successful_referrals': successful_referrals,
        }

    @staticmethod
    def get_revenue_stats():
        """
        Return revenue-related analytics.

        - mrr: monthly recurring revenue from currently active subscriptions
          (plan price / plan duration in months)
        - total_revenue: sum of all completed transactions
        - revenue_by_plan: list of {plan_name, total_revenue, transaction_count}
        - avg_transaction_amount: average amount of completed transactions
        """
        today = timezone.now().date()

        # MRR: for each active subscription, monthly contribution = price / duration_months
        active_subscriptions = Subscription.objects.filter(
            status='active',
            end_date__gte=today,
        ).select_related('plan')

        mrr = sum(
            float(sub.plan.price) / sub.plan.duration_months
            for sub in active_subscriptions
            if sub.plan.duration_months > 0
        )

        # Total revenue from completed transactions
        revenue_agg = Transaction.objects.filter(
            status='completed'
        ).aggregate(
            total_revenue=Sum('amount'),
            avg_transaction_amount=Avg('amount'),
        )

        total_revenue = float(revenue_agg['total_revenue'] or 0)
        avg_transaction_amount = float(revenue_agg['avg_transaction_amount'] or 0)

        # Revenue grouped by subscription plan name
        revenue_by_plan = list(
            Transaction.objects.filter(
                status='completed',
                subscription__isnull=False,
            ).values(
                plan_name=F('subscription__plan__name'),
            ).annotate(
                total_revenue=Sum('amount'),
                transaction_count=Count('id'),
            ).order_by('-total_revenue')
        )

        return {
            'mrr': round(mrr, 2),
            'total_revenue': round(total_revenue, 2),
            'revenue_by_plan': revenue_by_plan,
            'avg_transaction_amount': round(avg_transaction_amount, 2),
        }

    @staticmethod
    def get_user_activity_heatmap():
        """
        Return a heatmap-friendly structure of user activity counts
        grouped by hour of day (0-23) and day of week (0=Mon to 6=Sun).

        Django's ExtractWeekDay returns 1=Sunday .. 7=Saturday (database
        dependent), so we normalise to ISO weekday: 0=Monday .. 6=Sunday.
        """
        raw = (
            UserActivity.objects
            .annotate(
                hour=ExtractHour('created_at'),
                dow=ExtractWeekDay('created_at'),  # 1=Sun..7=Sat
            )
            .values('hour', 'dow')
            .annotate(count=Count('id'))
            .order_by('dow', 'hour')
        )

        # Normalise Django's weekday (1=Sun..7=Sat) to 0=Mon..6=Sun
        def _normalise_dow(django_dow):
            # 1=Sun->6, 2=Mon->0, 3=Tue->1 ... 7=Sat->5
            return (django_dow - 2) % 7

        heatmap = []
        for entry in raw:
            heatmap.append({
                'hour': entry['hour'],
                'day_of_week': _normalise_dow(entry['dow']),
                'count': entry['count'],
            })

        return heatmap

    @staticmethod
    def get_template_usage_stats():
        """
        For each template return:
        - template id, name, category
        - usage_count: number of resumes using this template
        - avg_ats_score: average ATS score for resumes using this template
        """
        templates = Template.objects.annotate(
            usage_count=Count('resumes', distinct=True),
            avg_ats_score=Avg('resumes__ats_scores__score'),
        ).values(
            'id', 'name', 'category__name',
            'is_premium', 'usage_count', 'avg_ats_score',
        ).order_by('-usage_count')

        result = []
        for t in templates:
            result.append({
                'id': t['id'],
                'name': t['name'],
                'category': t['category__name'],
                'is_premium': t['is_premium'],
                'usage_count': t['usage_count'],
                'avg_ats_score': round(t['avg_ats_score'], 2) if t['avg_ats_score'] else None,
            })

        return result

    @staticmethod
    def get_ats_stats():
        """
        Comprehensive ATS analytics:

        - top_job_titles: top 10 most-analysed job titles
        - avg_score_by_category: average of each category key inside
          ATSScore.analysis JSON (keyword, skills, structure, formatting)
        - score_distribution: count of scores in 5 buckets
          (0-20, 21-40, 41-60, 61-80, 81-100)
        - most_common_missing_keywords: top 20 keywords from KeywordMatch
          where found=False, ordered by frequency
        """
        # Top 10 job titles
        top_job_titles = list(
            ATSScore.objects
            .values('job_title')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Average score by analysis category
        # The analysis JSON is expected to have keys like:
        # {"keyword": 75, "skills": 80, "structure": 60, "formatting": 90}
        # We iterate in Python because JSON key extraction varies by DB backend.
        categories = ['keyword', 'skills', 'structure', 'formatting']
        category_totals = {c: [] for c in categories}

        for entry in ATSScore.objects.values_list('analysis', flat=True).iterator():
            if isinstance(entry, dict):
                for cat in categories:
                    val = entry.get(cat)
                    if val is not None:
                        try:
                            category_totals[cat].append(float(val))
                        except (TypeError, ValueError):
                            pass

        avg_score_by_category = {}
        for cat, values in category_totals.items():
            if values:
                avg_score_by_category[cat] = round(sum(values) / len(values), 2)
            else:
                avg_score_by_category[cat] = None

        # Score distribution
        score_distribution = list(
            ATSScore.objects.aggregate(
                range_0_20=Count('id', filter=Q(score__lte=20)),
                range_21_40=Count('id', filter=Q(score__gte=21, score__lte=40)),
                range_41_60=Count('id', filter=Q(score__gte=41, score__lte=60)),
                range_61_80=Count('id', filter=Q(score__gte=61, score__lte=80)),
                range_81_100=Count('id', filter=Q(score__gte=81, score__lte=100)),
            ).items()
        )
        score_distribution = [
            {'range': key.replace('range_', '').replace('_', '-'), 'count': val}
            for key, val in score_distribution
        ]

        # Most common missing keywords
        missing_keywords = list(
            KeywordMatch.objects
            .filter(found=False)
            .values('keyword')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )

        return {
            'top_job_titles': top_job_titles,
            'avg_score_by_category': avg_score_by_category,
            'score_distribution': score_distribution,
            'most_common_missing_keywords': missing_keywords,
        }

    @staticmethod
    def get_optimization_impact():
        """
        Measure the impact of optimization suggestions:

        - total_suggestions: total OptimizationSuggestion count
        - applied_count: suggestions that were applied
        - applied_rate: percentage of suggestions applied
        - avg_score_improvement: for users with multiple ATS scores,
          compute the average difference between their latest and earliest
          scores to approximate improvement over time
        """
        total_suggestions = OptimizationSuggestion.objects.count()
        applied_count = OptimizationSuggestion.objects.filter(applied=True).count()
        applied_rate = (
            round((applied_count / total_suggestions) * 100, 2)
            if total_suggestions > 0
            else 0
        )

        # Average score improvement: for each user who has 2+ ATS scores,
        # compare latest score vs earliest score.
        users_with_scores = (
            ATSScore.objects
            .values('user_id')
            .annotate(score_count=Count('id'))
            .filter(score_count__gte=2)
        )

        improvements = []
        for entry in users_with_scores:
            user_scores = ATSScore.objects.filter(
                user_id=entry['user_id']
            ).order_by('created_at')
            earliest = user_scores.first()
            latest = user_scores.last()
            if earliest and latest and earliest.pk != latest.pk:
                improvements.append(latest.score - earliest.score)

        avg_score_improvement = (
            round(sum(improvements) / len(improvements), 2)
            if improvements
            else 0
        )

        return {
            'total_suggestions': total_suggestions,
            'applied_count': applied_count,
            'applied_rate': applied_rate,
            'avg_score_improvement': avg_score_improvement,
        }

    @staticmethod
    def export_csv(data_type):
        """
        Generate CSV content for the requested data_type.

        Supported values:
        - 'users': id, username, email, full_name, role, is_verified,
          is_subscribed (has active sub), created_at
        - 'transactions': id, user, amount, currency, status,
          payment_method, transaction_id, created_at
        - 'scores': id, user, resume title, job_title, score, created_at

        Returns a string containing the CSV data.
        Raises ValueError for unsupported data_type.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if data_type == 'users':
            writer.writerow([
                'ID', 'Username', 'Email', 'Full Name', 'Role',
                'Is Verified', 'Is Subscribed', 'Created At',
            ])
            today = timezone.now().date()
            users = User.objects.filter(is_deleted=False).order_by('id')
            for user in users:
                is_subscribed = Subscription.objects.filter(
                    user=user,
                    status='active',
                    end_date__gte=today,
                ).exists()
                writer.writerow([
                    user.id,
                    user.username,
                    user.email,
                    user.full_name,
                    user.role,
                    user.is_verified,
                    is_subscribed,
                    user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                ])

        elif data_type == 'transactions':
            writer.writerow([
                'ID', 'User', 'Amount', 'Currency', 'Status',
                'Payment Method', 'Transaction ID', 'Created At',
            ])
            transactions = Transaction.objects.select_related('user').order_by('-created_at')
            for txn in transactions:
                writer.writerow([
                    txn.id,
                    txn.user.username,
                    str(txn.amount),
                    txn.currency,
                    txn.status,
                    txn.payment_method,
                    txn.transaction_id,
                    txn.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                ])

        elif data_type == 'scores':
            writer.writerow([
                'ID', 'User', 'Resume Title', 'Job Title',
                'Score', 'Created At',
            ])
            scores = ATSScore.objects.select_related('user', 'resume').order_by('-created_at')
            for s in scores:
                writer.writerow([
                    s.id,
                    s.user.username,
                    s.resume.title,
                    s.job_title,
                    s.score,
                    s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                ])

        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

        return output.getvalue()
