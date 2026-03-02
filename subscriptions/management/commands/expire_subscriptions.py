from django.core.management.base import BaseCommand
from django.utils import timezone
from subscriptions.models import Subscription


class Command(BaseCommand):
    help = 'Expire overdue active subscriptions'

    def handle(self, *args, **options):
        today = timezone.now().date()
        expired = Subscription.objects.filter(
            status='active',
            end_date__lt=today,
        ).update(status='expired')

        self.stdout.write(self.style.SUCCESS(f'Expired {expired} overdue subscriptions'))
