"""
Services for ATS Score Checker.
Uses spaCy and NLTK for NLP-powered resume analysis.
"""
import re
import logging
from typing import List

from .models import ATSScore, KeywordMatch, OptimizationSuggestion
from .nlp import SpaCyKeywordExtractor, SynonymExpander, TextAnalyzer

logger = logging.getLogger(__name__)

# Module-level instances (loaded once, reused)
_keyword_extractor = SpaCyKeywordExtractor()
_synonym_expander = SynonymExpander()
_text_analyzer = TextAnalyzer()


class ATSScoreAnalyzer:
    """Analyzes resumes against job descriptions using spaCy/NLTK NLP pipeline."""

    # Scoring weights: keyword 50%, skills 20%, structure 15%, formatting 15%
    KEYWORD_WEIGHT = 0.50
    SKILLS_WEIGHT = 0.20
    STRUCTURE_WEIGHT = 0.15
    FORMATTING_WEIGHT = 0.15

    def __init__(self, ats_score_obj: ATSScore):
        self.ats_score = ats_score_obj
        self.resume = ats_score_obj.resume
        self.resume_content = self.resume.content
        self.job_title = ats_score_obj.job_title
        self.job_description = ats_score_obj.job_description

        self.score = 0
        self.analysis = {}
        self.suggestions = []
        self.job_keywords = []
        self.resume_keywords = []

    def analyze(self) -> ATSScore:
        """Run the full analysis pipeline."""
        try:
            # 1. Extract keywords from job description and resume
            self.job_keywords = _keyword_extractor.extract_keywords(
                self.job_title + " " + self.job_description
            )
            resume_text = self._get_resume_text()
            self.resume_keywords = _keyword_extractor.extract_keywords(resume_text)

            # 2. Calculate keyword match score (with synonym expansion)
            keyword_score = self._calculate_keyword_match(resume_text)

            # 3. Calculate skills gap score
            skills_gap = _text_analyzer.identify_skills_gap(self.resume_keywords, self.job_keywords)
            skills_score = max(0, 100 - len(skills_gap) * 5)  # -5 per missing skill, min 0
            self.analysis['skills_gap'] = {
                'score': skills_score,
                'missing_skills': skills_gap,
            }

            # 4. Analyze structure
            structure_result = _text_analyzer.analyze_structure(self.resume_content)
            structure_score = structure_result['score']
            self.analysis['structure'] = structure_result

            # 5. Analyze formatting
            formatting_result = _text_analyzer.analyze_formatting(self.resume_content)
            formatting_score = formatting_result['score']
            self.analysis['formatting'] = formatting_result

            # 6. Calculate overall score
            self.score = int(
                self.KEYWORD_WEIGHT * keyword_score
                + self.SKILLS_WEIGHT * skills_score
                + self.STRUCTURE_WEIGHT * structure_score
                + self.FORMATTING_WEIGHT * formatting_score
            )
            self.score = min(100, max(0, self.score))

            # 7. Generate suggestions
            self._generate_suggestions(resume_text, skills_gap)

            # 8. Save results
            self.ats_score.score = self.score
            self.ats_score.analysis = self.analysis
            self.ats_score.suggestions = self.suggestions
            self.ats_score.save()

            self._save_keyword_matches()
            self._save_optimization_suggestions()

            return self.ats_score

        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}", exc_info=True)
            self.ats_score.score = 0
            self.ats_score.analysis = {"error": str(e)}
            self.ats_score.save()
            return self.ats_score

    def _calculate_keyword_match(self, resume_text: str) -> float:
        """Calculate keyword match score using NLP synonym expansion."""
        if not self.job_keywords:
            return 0

        resume_text_lower = resume_text.lower()
        total_weight = 0
        matched_weight = 0

        for kw in self.job_keywords:
            keyword = kw['keyword']
            importance = kw.get('importance', 'low')
            weight = 3 if importance == 'high' else 2 if importance == 'medium' else 1
            total_weight += weight

            # Check exact match
            found = keyword.lower() in resume_text_lower

            # If not found, check via synonym expansion
            if not found:
                synonyms = _synonym_expander.expand(keyword)
                for syn in synonyms:
                    if syn.lower() in resume_text_lower:
                        found = True
                        break

            # If still not found, check via stem matching against resume keywords
            if not found:
                for rkw in self.resume_keywords:
                    if _synonym_expander.are_related(keyword, rkw['keyword']):
                        found = True
                        break

            if found:
                matched_weight += weight
                kw['found'] = True
                match = re.search(r'[^.]*\b' + re.escape(keyword) + r'\b[^.]*', resume_text, re.IGNORECASE)
                kw['context'] = match.group(0).strip() if match else ''
            else:
                kw['found'] = False
                kw['context'] = ''

        score = (matched_weight / total_weight * 100) if total_weight > 0 else 0

        self.analysis['keyword_match'] = {
            'score': score,
            'matched_keywords': sum(1 for k in self.job_keywords if k.get('found')),
            'total_keywords': len(self.job_keywords),
            'details': self.job_keywords,
        }
        return score

    def _generate_suggestions(self, resume_text: str, skills_gap: List[dict]) -> None:
        """Generate improvement suggestions."""
        suggestions = []

        # Missing keywords
        missing = [k['keyword'] for k in self.job_keywords
                   if k.get('importance') in ('high', 'medium') and not k.get('found')]
        if missing:
            suggestions.append({
                'type': 'missing_keywords',
                'section': 'general',
                'description': f"Add these important keywords: {', '.join(missing[:10])}",
                'keywords': missing[:10],
            })

        # Missing skills
        if skills_gap:
            skill_names = [s['keyword'] for s in skills_gap[:8]]
            suggestions.append({
                'type': 'missing_skills',
                'section': 'skills',
                'description': f"Consider adding these skills: {', '.join(skill_names)}",
                'skills': skill_names,
            })

        # Missing sections
        if 'structure' in self.analysis:
            details = self.analysis['structure'].get('details', {})
            missing_sections = [s for s, info in details.items() if not info.get('present')]
            if missing_sections:
                suggestions.append({
                    'type': 'missing_sections',
                    'section': 'structure',
                    'description': f"Add these sections: {', '.join(missing_sections)}",
                    'sections': missing_sections,
                })

        # Formatting issues
        if 'formatting' in self.analysis:
            for issue in self.analysis['formatting'].get('issues', [])[:5]:
                suggestions.append({
                    'type': 'formatting',
                    'section': issue.get('section', 'general'),
                    'description': issue.get('issue', ''),
                })

        # Experience phrasing suggestions
        phrasing = _text_analyzer.suggest_experience_phrasing(resume_text)
        for p in phrasing[:5]:
            suggestions.append({
                'type': 'phrasing',
                'section': 'experience',
                'description': p.get('suggestion', ''),
                'original': p.get('original', ''),
                'reason': p.get('reason', ''),
            })

        self.suggestions = suggestions

    def _save_keyword_matches(self) -> None:
        """Save keyword matches to database."""
        matches = []
        for kw in self.job_keywords:
            matches.append(KeywordMatch(
                ats_score=self.ats_score,
                keyword=kw['keyword'],
                found=kw.get('found', False),
                importance=kw.get('importance', 'low'),
                context=kw.get('context', ''),
            ))
        KeywordMatch.objects.bulk_create(matches)

    def _save_optimization_suggestions(self) -> None:
        """Save optimization suggestions to database."""
        objs = []
        for suggestion in self.suggestions:
            objs.append(OptimizationSuggestion(
                ats_score=self.ats_score,
                section=suggestion.get('section', 'general'),
                original_text=suggestion.get('original', ''),
                suggested_text=suggestion.get('description', ''),
                reason=suggestion.get('reason', suggestion.get('description', '')),
            ))
        OptimizationSuggestion.objects.bulk_create(objs)

    def _get_resume_text(self) -> str:
        """Convert resume content JSON to plain text."""
        if isinstance(self.resume_content, dict):
            parts = []
            for section, content in self.resume_content.items():
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            parts.append(" ".join(str(v) for v in item.values()))
                        else:
                            parts.append(str(item))
                elif isinstance(content, dict):
                    parts.append(" ".join(str(v) for v in content.values()))
            return " ".join(parts)
        elif isinstance(self.resume_content, str):
            return self.resume_content
        return str(self.resume_content)


def analyze_resume(ats_score_id: int) -> ATSScore:
    """Analyze a resume against a job description. Called from Celery task."""
    try:
        ats_score = ATSScore.objects.get(id=ats_score_id)
        analyzer = ATSScoreAnalyzer(ats_score)
        return analyzer.analyze()
    except ATSScore.DoesNotExist:
        logger.error(f"ATSScore with ID {ats_score_id} does not exist")
        return None
    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}", exc_info=True)
        return None


def apply_suggestion(suggestion_id: int) -> bool:
    """Mark a suggestion as applied."""
    try:
        suggestion = OptimizationSuggestion.objects.get(id=suggestion_id)
        if suggestion.applied:
            return False
        suggestion.applied = True
        suggestion.save()
        return True
    except OptimizationSuggestion.DoesNotExist:
        logger.error(f"OptimizationSuggestion with ID {suggestion_id} does not exist")
        return False
