"""
Synonym expansion using NLTK WordNet and Porter stemming.

Provides two main capabilities:
1. Expanding a keyword into a list of related synonyms so that ATS matching
   can detect equivalent terms (e.g. "developer" <-> "engineer").
2. Checking whether two words are related (via shared stems or synsets).

Domain-specific synonyms stored in the ``JobTitleSynonym`` model are used
as a fallback when WordNet coverage is insufficient.
"""

import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy NLTK bootstrapping
# ---------------------------------------------------------------------------
_nltk_ready = False
_stemmer = None


def _ensure_nltk():
    """
    Download required NLTK data packages (once per process) and initialize
    the Porter stemmer.
    """
    global _nltk_ready, _stemmer
    if _nltk_ready:
        return True

    try:
        import nltk
        from nltk.stem import PorterStemmer

        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)

        _stemmer = PorterStemmer()
        _nltk_ready = True
        return True

    except ImportError:
        logger.warning(
            "NLTK is not installed. Install it with: pip install nltk"
        )
        return False


def _get_stemmer():
    """Return the cached Porter stemmer instance."""
    _ensure_nltk()
    return _stemmer


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class SynonymExpander:
    """
    Expand keywords into synonyms and check relatedness.

    Usage::

        expander = SynonymExpander()
        syns = expander.expand("developer")
        related = expander.are_related("developer", "engineer")
    """

    def __init__(self, max_synonyms: int = 10):
        self.max_synonyms = max_synonyms

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def expand(self, keyword: str) -> List[str]:
        """
        Return a list of synonyms for *keyword*.

        Sources (in order):
        1. NLTK WordNet synsets
        2. The ``JobTitleSynonym`` model (domain-specific, from the database)

        Duplicates and the original keyword itself are removed.
        """
        keyword = keyword.strip().lower()
        if not keyword:
            return []

        synonyms: Set[str] = set()

        # 1. WordNet synonyms
        synonyms.update(self._wordnet_synonyms(keyword))

        # 2. Domain-specific synonyms from the database
        synonyms.update(self._db_synonyms(keyword))

        # Remove the original keyword from the results
        synonyms.discard(keyword)

        # Sort alphabetically for deterministic output and cap at max
        return sorted(synonyms)[: self.max_synonyms]

    def are_related(self, word1: str, word2: str) -> bool:
        """
        Return ``True`` if *word1* and *word2* are related.

        Two words are considered related when any of the following hold:
        - They share the same Porter stem.
        - They appear in the same WordNet synset.
        - One appears in the synonym list of the other in the database.
        """
        w1 = word1.strip().lower()
        w2 = word2.strip().lower()

        if w1 == w2:
            return True

        # Stem check
        if self._stems_match(w1, w2):
            return True

        # WordNet synset overlap
        if self._synsets_overlap(w1, w2):
            return True

        # Database synonym check
        if self._db_related(w1, w2):
            return True

        return False

    # ------------------------------------------------------------------
    # WordNet helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wordnet_synonyms(keyword: str) -> Set[str]:
        """Retrieve lemma names from WordNet synsets for *keyword*."""
        if not _ensure_nltk():
            return set()

        try:
            from nltk.corpus import wordnet

            synonyms: Set[str] = set()
            for synset in wordnet.synsets(keyword):
                for lemma in synset.lemmas():
                    name = lemma.name().replace("_", " ").lower()
                    if name != keyword:
                        synonyms.add(name)
            return synonyms

        except Exception as exc:
            logger.debug("WordNet lookup failed for '%s': %s", keyword, exc)
            return set()

    @staticmethod
    def _synsets_overlap(word1: str, word2: str) -> bool:
        """Return True if *word1* and *word2* share a WordNet synset."""
        if not _ensure_nltk():
            return False

        try:
            from nltk.corpus import wordnet

            synsets1 = set(wordnet.synsets(word1))
            synsets2 = set(wordnet.synsets(word2))
            return bool(synsets1 & synsets2)

        except Exception:
            return False

    # ------------------------------------------------------------------
    # Stemmer helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stems_match(word1: str, word2: str) -> bool:
        """Return True if both words reduce to the same Porter stem."""
        stemmer = _get_stemmer()
        if stemmer is None:
            return False
        return stemmer.stem(word1) == stemmer.stem(word2)

    # ------------------------------------------------------------------
    # Database (JobTitleSynonym) helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _db_synonyms(keyword: str) -> Set[str]:
        """
        Look up domain-specific synonyms from the ``JobTitleSynonym`` model.

        Returns an empty set if the model is unavailable (e.g. database not
        migrated yet).
        """
        try:
            from ats_checker.models import JobTitleSynonym

            synonyms: Set[str] = set()

            # Check if the keyword itself is a stored title
            try:
                entry = JobTitleSynonym.objects.get(title__iexact=keyword)
                for syn in entry.synonyms:
                    synonyms.add(str(syn).lower())
            except JobTitleSynonym.DoesNotExist:
                pass

            # Also check if the keyword appears as a synonym of another title
            entries = JobTitleSynonym.objects.all()
            for entry in entries:
                syn_list = [str(s).lower() for s in entry.synonyms]
                if keyword in syn_list:
                    synonyms.add(entry.title.lower())
                    synonyms.update(syn_list)

            return synonyms

        except Exception as exc:
            logger.debug("Database synonym lookup failed: %s", exc)
            return set()

    @staticmethod
    def _db_related(word1: str, word2: str) -> bool:
        """
        Return True if *word1* and *word2* are linked through the
        ``JobTitleSynonym`` model.
        """
        try:
            from ats_checker.models import JobTitleSynonym

            # Check word1 as title, word2 in synonyms
            try:
                entry = JobTitleSynonym.objects.get(title__iexact=word1)
                if word2 in [str(s).lower() for s in entry.synonyms]:
                    return True
            except JobTitleSynonym.DoesNotExist:
                pass

            # Check word2 as title, word1 in synonyms
            try:
                entry = JobTitleSynonym.objects.get(title__iexact=word2)
                if word1 in [str(s).lower() for s in entry.synonyms]:
                    return True
            except JobTitleSynonym.DoesNotExist:
                pass

            # Check if both appear in the same synonym group
            for entry in JobTitleSynonym.objects.all():
                group = {entry.title.lower()} | {
                    str(s).lower() for s in entry.synonyms
                }
                if word1 in group and word2 in group:
                    return True

            return False

        except Exception:
            return False
