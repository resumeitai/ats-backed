"""
NLP module for the ATS checker.

Provides spaCy/NLTK-powered keyword extraction, synonym expansion,
text analysis, and a comprehensive skills database -- replacing the
original regex-based approach in ``ats_checker.services``.

Quick start::

    from ats_checker.nlp import (
        SpaCyKeywordExtractor,
        SynonymExpander,
        TextAnalyzer,
        get_skill_category,
        is_known_skill,
        SKILLS_DB,
    )

    extractor = SpaCyKeywordExtractor()
    keywords = extractor.extract_keywords(job_description_text)

    expander = SynonymExpander()
    synonyms = expander.expand("developer")

    analyzer = TextAnalyzer()
    structure = analyzer.analyze_structure(resume_content_dict)
"""

from .keyword_extractor import SpaCyKeywordExtractor
from .synonym_expander import SynonymExpander
from .text_analyzer import TextAnalyzer
from .skills_db import SKILLS_DB, get_skill_category, is_known_skill
from .multilang import (
    MultiLangKeywordExtractor,
    detect_language,
    get_supported_languages,
)

__all__ = [
    "SpaCyKeywordExtractor",
    "SynonymExpander",
    "TextAnalyzer",
    "SKILLS_DB",
    "get_skill_category",
    "is_known_skill",
    "MultiLangKeywordExtractor",
    "detect_language",
    "get_supported_languages",
]
