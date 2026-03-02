"""
Resume text analysis: structure checking, formatting evaluation,
keyword density, skills-gap identification, and experience phrasing
suggestions.

All analysis methods accept the resume ``content`` dict (a JSONField from
the ``Resume`` model) or plain text as appropriate.
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from .skills_db import get_skill_category, is_known_skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load spaCy (reuse the cached model from keyword_extractor)
# ---------------------------------------------------------------------------


def _get_nlp():
    """Return the cached spaCy model, or None if unavailable."""
    try:
        from .keyword_extractor import _load_spacy_model

        return _load_spacy_model()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The canonical sections a well-formed resume should contain, in a
# recommended ordering.
EXPECTED_SECTIONS = [
    "personal",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
]

# Recommended ordering (lower index == should appear earlier)
_SECTION_ORDER = {section: idx for idx, section in enumerate(EXPECTED_SECTIONS)}

# Strong action verbs that ATS systems look for at the start of experience
# bullet points.
ACTION_VERBS = frozenset(
    {
        "achieved", "administered", "analyzed", "architected", "automated",
        "built", "collaborated", "conducted", "configured", "coordinated",
        "created", "delivered", "deployed", "designed", "developed",
        "directed", "drove", "enabled", "engineered", "established",
        "evaluated", "executed", "expanded", "facilitated", "founded",
        "generated", "headed", "implemented", "improved", "increased",
        "influenced", "initiated", "integrated", "introduced", "launched",
        "led", "maintained", "managed", "mentored", "migrated",
        "monitored", "negotiated", "optimized", "orchestrated", "organized",
        "oversaw", "performed", "pioneered", "planned", "presented",
        "produced", "programmed", "proposed", "provided", "published",
        "reduced", "refactored", "re-engineered", "resolved", "revamped",
        "reviewed", "scaled", "secured", "simplified", "spearheaded",
        "streamlined", "strengthened", "supervised", "supported",
        "surpassed", "tested", "trained", "transformed", "troubleshot",
        "upgraded", "utilized",
    }
)

# Date patterns commonly found in resumes (e.g. "Jan 2020 - Present")
_DATE_PATTERNS = [
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
    r"\b\d{1,2}/\d{4}\b",
    r"\b\d{4}\s*[-\u2013]\s*(?:\d{4}|[Pp]resent|[Cc]urrent)\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\s*[-\u2013]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|[Pp]resent|[Cc]urrent)\b",
]

# Vague / weak phrases that should be replaced with quantified language
_VAGUE_PHRASES = [
    (r"\bresponsible for\b", "Replace 'responsible for' with a strong action verb (e.g. 'managed', 'led', 'developed')"),
    (r"\bhelped with\b", "Replace 'helped with' with a specific contribution (e.g. 'contributed to', 'co-developed')"),
    (r"\bworked on\b", "Replace 'worked on' with a more specific verb (e.g. 'developed', 'designed', 'implemented')"),
    (r"\bvarious\b", "Replace 'various' with specific details or quantities"),
    (r"\bsuccessfully\b", "Remove 'successfully' and show success through quantified results instead"),
    (r"\bduties included\b", "Replace 'duties included' with action-verb bullet points"),
    (r"\btasked with\b", "Replace 'tasked with' with an active verb describing what you did"),
    (r"\bassisted in\b", "Replace 'assisted in' with a more specific contribution"),
]

# Minimum / maximum content length guidelines (approximate character counts)
_SECTION_LENGTH_MIN = 50       # characters
_SECTION_LENGTH_MAX = 5000     # characters


class TextAnalyzer:
    """
    Analyze resume text for structure, formatting, keyword density, skills
    gaps, and phrasing quality.

    Usage::

        analyzer = TextAnalyzer()
        structure = analyzer.analyze_structure(resume_content)
        formatting = analyzer.analyze_formatting(resume_content)
    """

    def __init__(self):
        self.nlp = _get_nlp()

    # ==================================================================
    # 1. Structure analysis
    # ==================================================================

    def analyze_structure(self, resume_content: dict) -> dict:
        """
        Evaluate which sections are present and whether they follow the
        recommended ordering.

        Args:
            resume_content: The ``content`` JSONField from a Resume object.

        Returns:
            dict with keys:
                score    (int)  - 0-100
                details  (dict) - per-section presence and ordering info
        """
        if not isinstance(resume_content, dict):
            return {"score": 0, "details": {"error": "Resume content is not a dict"}}

        content_keys = {k.lower() for k in resume_content.keys()}

        found: list[str] = []
        missing: list[str] = []

        for section in EXPECTED_SECTIONS:
            if section in content_keys:
                found.append(section)
            else:
                missing.append(section)

        # ---- Score: section presence (up to 70 points) ----
        # personal/education/experience/skills are critical; projects and
        # certifications are nice-to-have.
        critical = {"personal", "education", "experience", "skills"}
        optional = {"projects", "certifications"}

        critical_found = len(critical & set(found))
        optional_found = len(optional & set(found))

        presence_score = (critical_found / len(critical)) * 60 + (
            optional_found / len(optional)
        ) * 10

        # ---- Score: ordering (up to 30 points) ----
        # Check whether the found sections respect the recommended order.
        found_indices = [_SECTION_ORDER.get(s, 99) for s in found]
        order_violations = 0
        for i in range(1, len(found_indices)):
            if found_indices[i] < found_indices[i - 1]:
                order_violations += 1

        if len(found) > 1:
            order_score = max(0, 30 - order_violations * 10)
        else:
            order_score = 0

        total_score = min(100, int(presence_score + order_score))

        return {
            "score": total_score,
            "details": {
                "found_sections": found,
                "missing_sections": missing,
                "order_violations": order_violations,
                "recommendations": self._section_recommendations(missing),
            },
        }

    @staticmethod
    def _section_recommendations(missing: list[str]) -> list[str]:
        """Generate human-readable recommendations for missing sections."""
        tips = {
            "personal": "Add a 'Personal' section with your name, contact information, and professional summary.",
            "education": "Add an 'Education' section listing your degrees, institutions, and graduation dates.",
            "experience": "Add an 'Experience' section with your work history, accomplishments, and dates.",
            "skills": "Add a 'Skills' section listing your technical and soft skills.",
            "projects": "Consider adding a 'Projects' section to showcase relevant work.",
            "certifications": "Consider adding a 'Certifications' section if you hold industry certifications.",
        }
        return [tips[s] for s in missing if s in tips]

    # ==================================================================
    # 2. Formatting analysis
    # ==================================================================

    def analyze_formatting(self, resume_content: dict) -> dict:
        """
        Check content length, bullet-point usage, action verbs, and date
        consistency across sections.

        Args:
            resume_content: The ``content`` JSONField from a Resume object.

        Returns:
            dict with keys:
                score  (int)       - 0-100
                issues (list[str]) - human-readable issue descriptions
        """
        if not isinstance(resume_content, dict):
            return {"score": 0, "issues": ["Resume content is not a dict"]}

        issues: list[str] = []
        deductions = 0

        for section_name, section_data in resume_content.items():
            section_text = self._section_to_text(section_data)
            section_lower = section_name.lower()

            # -- Content length --
            length = len(section_text)
            if length < _SECTION_LENGTH_MIN:
                issues.append(
                    f"Section '{section_name}' is very short ({length} chars). "
                    "Consider adding more detail."
                )
                deductions += 5
            elif length > _SECTION_LENGTH_MAX:
                issues.append(
                    f"Section '{section_name}' is very long ({length} chars). "
                    "Consider being more concise."
                )
                deductions += 3

            # -- Bullet point usage (experience / projects) --
            if section_lower in ("experience", "projects"):
                bullet_lines = [
                    line
                    for line in section_text.splitlines()
                    if line.strip().startswith(("-", "*", "\u2022"))
                ]
                total_lines = [
                    line for line in section_text.splitlines() if line.strip()
                ]
                if total_lines and not bullet_lines:
                    issues.append(
                        f"Section '{section_name}' does not use bullet points. "
                        "Bullet points improve readability for ATS systems."
                    )
                    deductions += 10

            # -- Action verbs at start of experience entries --
            if section_lower == "experience":
                self._check_action_verbs(section_text, issues)

            # -- Date consistency --
            if section_lower in ("experience", "education"):
                self._check_date_consistency(section_text, section_name, issues)

        # Calculate score
        score = max(0, 100 - deductions)

        return {"score": score, "issues": issues}

    def _check_action_verbs(self, text: str, issues: list[str]) -> None:
        """Check whether experience bullet points start with action verbs."""
        lines = [
            line.strip().lstrip("-*\u2022 ")
            for line in text.splitlines()
            if line.strip()
        ]
        non_action_count = 0
        for line in lines:
            first_word = line.split()[0].lower().rstrip(".,;:") if line.split() else ""
            if first_word and first_word not in ACTION_VERBS and len(line) > 20:
                non_action_count += 1

        if non_action_count > 0 and lines:
            ratio = non_action_count / len(lines)
            if ratio > 0.5:
                issues.append(
                    f"{non_action_count} of {len(lines)} experience entries do not "
                    "start with a strong action verb. Use verbs like 'Developed', "
                    "'Implemented', 'Led', 'Designed' to strengthen your resume."
                )

    @staticmethod
    def _check_date_consistency(
        text: str, section_name: str, issues: list[str]
    ) -> None:
        """Check whether dates in a section follow a consistent format."""
        found_formats: list[str] = []
        for pattern in _DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_formats.append(pattern)

        if len(found_formats) == 0 and len(text) > _SECTION_LENGTH_MIN:
            issues.append(
                f"No dates found in '{section_name}'. Include dates to "
                "show your timeline."
            )
        elif len(found_formats) > 2:
            issues.append(
                f"Multiple date formats detected in '{section_name}'. "
                "Use a single consistent format (e.g. 'Jan 2020 - Dec 2022')."
            )

    # ==================================================================
    # 3. Keyword density
    # ==================================================================

    def calculate_keyword_density(
        self, text: str, keywords: List[str]
    ) -> dict:
        """
        Calculate how frequently each keyword appears in *text*.

        Args:
            text: The full resume text.
            keywords: List of target keywords.

        Returns:
            dict with keys:
                total_words     (int)
                keyword_counts  (dict[str, int])
                densities       (dict[str, float]) - percentage per keyword
                overall_density (float) - total keyword occurrences / total words
        """
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)
        total_words = len(words)

        if total_words == 0:
            return {
                "total_words": 0,
                "keyword_counts": {},
                "densities": {},
                "overall_density": 0.0,
            }

        keyword_counts: Dict[str, int] = {}
        densities: Dict[str, float] = {}

        for kw in keywords:
            kw_lower = kw.lower()
            count = len(re.findall(r"\b" + re.escape(kw_lower) + r"\b", text_lower))
            keyword_counts[kw] = count
            densities[kw] = round((count / total_words) * 100, 2)

        total_kw_count = sum(keyword_counts.values())
        overall_density = round((total_kw_count / total_words) * 100, 2)

        return {
            "total_words": total_words,
            "keyword_counts": keyword_counts,
            "densities": densities,
            "overall_density": overall_density,
        }

    # ==================================================================
    # 4. Skills gap
    # ==================================================================

    def identify_skills_gap(
        self,
        resume_keywords: List[dict],
        job_keywords: List[dict],
    ) -> List[dict]:
        """
        Identify skills present in the job description but missing from the
        resume.

        Args:
            resume_keywords: Output of ``SpaCyKeywordExtractor.extract_keywords``
                             run on the resume text.
            job_keywords:    Output of ``SpaCyKeywordExtractor.extract_keywords``
                             run on the job description.

        Returns:
            List of dicts with keys: keyword, importance, category
            sorted by importance (high first).
        """
        resume_kw_set = {kw["keyword"].lower() for kw in resume_keywords}

        missing = []
        for jk in job_keywords:
            if jk["keyword"].lower() not in resume_kw_set:
                missing.append(
                    {
                        "keyword": jk["keyword"],
                        "importance": jk.get("importance", "low"),
                        "category": jk.get("category", "general"),
                    }
                )

        # Sort by importance
        importance_order = {"high": 0, "medium": 1, "low": 2}
        missing.sort(key=lambda m: importance_order.get(m["importance"], 3))
        return missing

    # ==================================================================
    # 5. Experience phrasing suggestions
    # ==================================================================

    def suggest_experience_phrasing(self, text: str) -> List[dict]:
        """
        Analyze experience text and return phrasing suggestions.

        Checks for:
        - Passive voice (via spaCy dependency parsing)
        - Vague / weak phrases

        Args:
            text: The experience section text.

        Returns:
            List of dicts with keys: original, suggestion, reason
        """
        suggestions: list[dict] = []

        # 1. Passive voice detection (requires spaCy)
        if self.nlp is not None:
            suggestions.extend(self._detect_passive_voice(text))

        # 2. Vague phrase detection (regex-based, always available)
        suggestions.extend(self._detect_vague_phrases(text))

        return suggestions

    def _detect_passive_voice(self, text: str) -> List[dict]:
        """
        Use spaCy dependency parsing to find passive-voice constructions
        and suggest active-voice alternatives.
        """
        results: list[dict] = []
        if self.nlp is None:
            return results

        doc = self.nlp(text)

        for sent in doc.sents:
            has_passive = False
            passive_subject = ""
            passive_verb = ""

            for token in sent:
                if token.dep_ in ("nsubjpass", "auxpass"):
                    has_passive = True
                    if token.dep_ == "nsubjpass":
                        passive_subject = token.text
                    if token.dep_ == "auxpass":
                        passive_verb = token.head.text

            if has_passive:
                original = sent.text.strip()
                if passive_verb:
                    suggestion = (
                        f"Rewrite in active voice. Consider starting with an "
                        f"action verb instead of the passive construction "
                        f"around '{passive_verb}'."
                    )
                else:
                    suggestion = (
                        "Rewrite this sentence in active voice, starting with "
                        "a strong action verb."
                    )

                results.append(
                    {
                        "original": original,
                        "suggestion": suggestion,
                        "reason": "Passive voice weakens impact. Active voice is preferred by ATS systems.",
                    }
                )

        return results

    @staticmethod
    def _detect_vague_phrases(text: str) -> List[dict]:
        """Detect vague or weak phrasing using regex patterns."""
        results: list[dict] = []

        for pattern, tip in _VAGUE_PHRASES:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                context = text[start:end].strip()

                results.append(
                    {
                        "original": context,
                        "suggestion": tip,
                        "reason": "Vague phrasing reduces resume impact and ATS relevance.",
                    }
                )

        return results

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _section_to_text(section_data: Any) -> str:
        """
        Convert a section value (str, list, or dict) from the resume
        content JSONField into a flat string for analysis.
        """
        if isinstance(section_data, str):
            return section_data

        if isinstance(section_data, list):
            parts = []
            for item in section_data:
                if isinstance(item, dict):
                    parts.append(
                        " ".join(str(v) for v in item.values())
                    )
                else:
                    parts.append(str(item))
            return "\n".join(parts)

        if isinstance(section_data, dict):
            return " ".join(str(v) for v in section_data.values())

        return str(section_data)
