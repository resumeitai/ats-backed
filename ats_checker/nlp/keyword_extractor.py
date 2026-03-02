"""
Keyword extraction using spaCy NLP pipeline.

Replaces the regex-based keyword extraction in the original services module
with proper NER, noun-phrase extraction, and a custom entity ruler for
common technology skills.
"""

import logging
import re
from collections import Counter
from typing import List, Optional

from .skills_db import SKILLS_DB, get_skill_category, is_known_skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load spaCy model once at module level (cached for the lifetime of the
# process).  A fallback to the smaller model is attempted if `en_core_web_lg`
# is not installed.
# ---------------------------------------------------------------------------
_nlp = None


def _load_spacy_model():
    """Load and return the spaCy NLP model, with caching."""
    global _nlp
    if _nlp is not None:
        return _nlp

    try:
        import spacy
    except ImportError:
        logger.warning(
            "spaCy is not installed. Install it with: pip install spacy"
        )
        return None

    for model_name in ("en_core_web_lg", "en_core_web_md", "en_core_web_sm"):
        try:
            _nlp = spacy.load(model_name)
            logger.info("Loaded spaCy model: %s", model_name)
            _add_entity_ruler(_nlp)
            return _nlp
        except OSError:
            continue

    logger.warning(
        "No spaCy English model found. "
        "Install one with: python -m spacy download en_core_web_lg"
    )
    return None


def _add_entity_ruler(nlp):
    """
    Add a custom EntityRuler with patterns for common tech skills so that
    they are recognized as SKILL entities even when the base model misses
    them.
    """
    try:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
    except ValueError:
        # entity_ruler already exists (e.g. model reloaded in tests)
        return

    patterns = []
    # Build patterns from the skills database
    for category, skills in SKILLS_DB.items():
        if category == "soft_skills":
            # Soft skills are usually multi-word; still useful to tag them
            label = "SOFT_SKILL"
        else:
            label = "SKILL"

        for skill in skills:
            tokens = skill.split()
            if len(tokens) == 1:
                patterns.append(
                    {"label": label, "pattern": [{"LOWER": skill.lower()}]}
                )
            else:
                patterns.append(
                    {
                        "label": label,
                        "pattern": [{"LOWER": t.lower()} for t in tokens],
                    }
                )

    ruler.add_patterns(patterns)


# ---------------------------------------------------------------------------
# Stopwords that should never surface as keywords
# ---------------------------------------------------------------------------
_EXTRA_STOPWORDS = frozenset(
    {
        "etc", "e.g", "i.e", "including", "also", "using", "use", "used",
        "work", "working", "able", "ability", "experience", "year", "years",
        "strong", "knowledge", "understanding", "good", "great", "excellent",
        "well", "best", "team", "role", "company", "job", "position",
        "candidate", "must", "required", "preferred", "looking", "seek",
        "seeking", "responsible", "responsibility", "responsibilities",
        "requirement", "requirements", "qualification", "qualifications",
        "will", "would", "should", "could", "may", "might",
    }
)

_MIN_KEYWORD_LENGTH = 2


class SpaCyKeywordExtractor:
    """
    Extract keywords from text using spaCy NER, noun-phrase chunking,
    and the built-in skills database.

    Usage::

        extractor = SpaCyKeywordExtractor()
        keywords = extractor.extract_keywords(job_description_text)
    """

    def __init__(self, max_keywords: int = 30):
        self.max_keywords = max_keywords
        self.nlp = _load_spacy_model()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_keywords(self, text: str) -> List[dict]:
        """
        Extract and rank keywords from *text*.

        Returns a list of dicts, each with keys:
            keyword   (str)  - the canonical keyword
            count     (int)  - how many times it appears in *text*
            importance (str) - 'high', 'medium', or 'low'
            category  (str)  - skill category or 'general'

        The list is sorted by importance (high first), then by count,
        and capped at ``self.max_keywords`` entries.
        """
        if not text or not text.strip():
            return []

        # If spaCy is not available, fall back to simple extraction
        if self.nlp is None:
            return self._fallback_extract(text)

        doc = self.nlp(text)

        # Collect candidate keywords from three sources
        candidates: Counter = Counter()
        category_map: dict[str, str] = {}

        # 1. Named entities (SKILL / SOFT_SKILL from the entity ruler,
        #    plus ORG, PRODUCT, GPE from the NER model)
        self._collect_entities(doc, candidates, category_map)

        # 2. Noun phrases (noun chunks)
        self._collect_noun_phrases(doc, candidates, category_map)

        # 3. Individual tokens that are known skills
        self._collect_known_skill_tokens(doc, candidates, category_map)

        # Build the result list
        results = self._rank_and_format(candidates, category_map)
        return results[: self.max_keywords]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_entities(
        self, doc, candidates: Counter, category_map: dict
    ) -> None:
        """Collect entities recognized by NER and the entity ruler."""
        useful_labels = {
            "SKILL", "SOFT_SKILL", "ORG", "PRODUCT", "GPE",
            "WORK_OF_ART", "LAW",
        }
        for ent in doc.ents:
            if ent.label_ not in useful_labels:
                continue
            key = ent.text.lower().strip()
            if self._is_stopword(key):
                continue
            candidates[key] += 1
            # Determine category
            if ent.label_ == "SKILL":
                category_map.setdefault(key, get_skill_category(key) or "technical")
            elif ent.label_ == "SOFT_SKILL":
                category_map.setdefault(key, "soft_skills")
            elif ent.label_ == "ORG":
                category_map.setdefault(key, "organization")
            else:
                category_map.setdefault(key, "general")

    def _collect_noun_phrases(
        self, doc, candidates: Counter, category_map: dict
    ) -> None:
        """Collect meaningful noun phrases from spaCy noun chunks."""
        for chunk in doc.noun_chunks:
            # Remove determiners / pronouns at the start
            phrase = chunk.text.lower().strip()
            phrase = re.sub(r"^(the|a|an|this|that|these|those|our|your|their)\s+", "", phrase)
            phrase = phrase.strip()

            if len(phrase) <= _MIN_KEYWORD_LENGTH:
                continue
            if self._is_stopword(phrase):
                continue
            # Prefer known skills
            cat = get_skill_category(phrase)
            if cat:
                candidates[phrase] += 1
                category_map.setdefault(phrase, cat)
            elif len(phrase.split()) <= 3:
                # Keep short noun phrases as general keywords
                candidates[phrase] += 1
                category_map.setdefault(phrase, "general")

    def _collect_known_skill_tokens(
        self, doc, candidates: Counter, category_map: dict
    ) -> None:
        """Check individual tokens against the skills database."""
        for token in doc:
            if token.is_stop or token.is_punct or token.is_space:
                continue
            word = token.text.lower().strip()
            if len(word) <= _MIN_KEYWORD_LENGTH:
                continue
            if is_known_skill(word):
                candidates[word] += 1
                category_map.setdefault(word, get_skill_category(word) or "technical")

    def _rank_and_format(
        self, candidates: Counter, category_map: dict
    ) -> List[dict]:
        """Assign importance and sort candidates."""
        if not candidates:
            return []

        max_count = max(candidates.values())

        results = []
        for keyword, count in candidates.items():
            # Importance heuristic: known skills get a boost
            cat = category_map.get(keyword, "general")
            is_skill = cat not in ("general", "organization")

            if is_skill and count >= 2:
                importance = "high"
            elif is_skill or count >= max(3, max_count * 0.5):
                importance = "medium"
            else:
                importance = "low"

            results.append(
                {
                    "keyword": keyword,
                    "count": count,
                    "importance": importance,
                    "category": cat,
                }
            )

        # Sort: high > medium > low, then by count descending
        importance_order = {"high": 0, "medium": 1, "low": 2}
        results.sort(key=lambda r: (importance_order[r["importance"]], -r["count"]))
        return results

    # ------------------------------------------------------------------
    # Fallback (no spaCy)
    # ------------------------------------------------------------------

    def _fallback_extract(self, text: str) -> List[dict]:
        """Simple regex-based extraction used when spaCy is unavailable."""
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9#+.\-]*\b", text.lower())
        counter: Counter = Counter()
        category_map: dict[str, str] = {}

        for word in words:
            if len(word) <= _MIN_KEYWORD_LENGTH:
                continue
            if self._is_stopword(word):
                continue
            counter[word] += 1
            if is_known_skill(word):
                category_map.setdefault(word, get_skill_category(word) or "technical")
            else:
                category_map.setdefault(word, "general")

        return self._rank_and_format(counter, category_map)[: self.max_keywords]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _is_stopword(word: str) -> bool:
        """Return True if *word* should be filtered out."""
        if word in _EXTRA_STOPWORDS:
            return True
        if len(word) <= _MIN_KEYWORD_LENGTH:
            return True
        return False
