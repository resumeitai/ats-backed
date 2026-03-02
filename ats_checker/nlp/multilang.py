"""
Multi-language resume support for the ATS checker.

Provides language detection and multi-language NLP processing
using spaCy's multi-language models.

Supported languages:
- English (en) — en_core_web_lg (primary)
- Hindi (hi) — xx_ent_wiki_sm fallback
- French (fr) — fr_core_news_sm
- German (de) — de_core_news_sm
- Spanish (es) — es_core_news_sm
- Chinese (zh) — zh_core_web_sm
- Japanese (ja) — ja_core_news_sm
"""
import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache loaded models
_models: Dict[str, object] = {}

# Language model mapping (language code → spaCy model names in preference order)
LANGUAGE_MODELS = {
    'en': ['en_core_web_lg', 'en_core_web_md', 'en_core_web_sm'],
    'fr': ['fr_core_news_lg', 'fr_core_news_md', 'fr_core_news_sm'],
    'de': ['de_core_news_lg', 'de_core_news_md', 'de_core_news_sm'],
    'es': ['es_core_news_lg', 'es_core_news_md', 'es_core_news_sm'],
    'zh': ['zh_core_web_lg', 'zh_core_web_md', 'zh_core_web_sm'],
    'ja': ['ja_core_news_lg', 'ja_core_news_md', 'ja_core_news_sm'],
    'hi': ['xx_ent_wiki_sm'],  # Hindi uses the multi-language model
    'xx': ['xx_ent_wiki_sm'],  # Multi-language fallback
}

# Common language detection patterns
_DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
_JAPANESE_RE = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
_FRENCH_INDICATORS = frozenset(['le', 'la', 'les', 'des', 'une', 'est', 'sont', 'avec', 'dans', 'pour', 'qui', 'que'])
_GERMAN_INDICATORS = frozenset(['der', 'die', 'das', 'und', 'ist', 'ein', 'eine', 'mit', 'von', 'für', 'auf'])
_SPANISH_INDICATORS = frozenset(['el', 'los', 'las', 'una', 'con', 'por', 'para', 'que', 'como', 'del'])


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.

    Returns a two-letter language code (e.g., 'en', 'hi', 'fr').
    Falls back to 'en' if detection is uncertain.
    """
    if not text or not text.strip():
        return 'en'

    # Script-based detection (high confidence)
    if _DEVANAGARI_RE.search(text):
        return 'hi'
    if _JAPANESE_RE.search(text):
        return 'ja'
    if _CJK_RE.search(text):
        return 'zh'

    # Word-frequency-based detection for Latin-script languages
    words = set(re.findall(r'\b[a-zA-Zéèêëàâîïôùûçüöäß]+\b', text.lower()))

    french_score = len(words & _FRENCH_INDICATORS)
    german_score = len(words & _GERMAN_INDICATORS)
    spanish_score = len(words & _SPANISH_INDICATORS)

    max_score = max(french_score, german_score, spanish_score)
    if max_score >= 3:
        if french_score == max_score:
            return 'fr'
        elif german_score == max_score:
            return 'de'
        elif spanish_score == max_score:
            return 'es'

    # Try spaCy langdetect if available
    try:
        from spacy.lang.en import English
        # Use spaCy's built-in language detection via spacy-langdetect if installed
        from spacy_langdetect import LanguageDetector
        nlp = English()
        nlp.add_pipe('language_detector', last=True)
        doc = nlp(text[:500])  # Only check first 500 chars for speed
        detected = doc._.language
        if detected and detected.get('score', 0) > 0.8:
            lang = detected.get('language', 'en')
            if lang in LANGUAGE_MODELS:
                return lang
    except (ImportError, Exception):
        pass

    return 'en'


def load_model(lang: str):
    """
    Load and return the spaCy NLP model for the given language.

    The model is cached after first load. Falls back to the
    multi-language model if the language-specific model is unavailable.
    """
    if lang in _models:
        return _models[lang]

    try:
        import spacy
    except ImportError:
        logger.warning("spaCy is not installed.")
        return None

    model_names = LANGUAGE_MODELS.get(lang, LANGUAGE_MODELS['xx'])

    for model_name in model_names:
        try:
            model = spacy.load(model_name)
            _models[lang] = model
            logger.info("Loaded spaCy model '%s' for language '%s'", model_name, lang)
            return model
        except OSError:
            continue

    # Final fallback: try the multi-language model
    if lang != 'xx':
        for model_name in LANGUAGE_MODELS['xx']:
            try:
                model = spacy.load(model_name)
                _models[lang] = model
                logger.info("Loaded fallback model '%s' for language '%s'", model_name, lang)
                return model
            except OSError:
                continue

    logger.warning(
        "No spaCy model available for language '%s'. "
        "Install one with: python -m spacy download %s",
        lang,
        model_names[0] if model_names else 'xx_ent_wiki_sm',
    )
    return None


class MultiLangKeywordExtractor:
    """
    Language-aware keyword extractor.

    Detects the language of the input text, loads the appropriate spaCy
    model, and extracts keywords using NER and noun-phrase chunking.

    Falls back to the English extractor (SpaCyKeywordExtractor) for
    English text.
    """

    def __init__(self, max_keywords: int = 30):
        self.max_keywords = max_keywords

    def extract_keywords(self, text: str, lang: Optional[str] = None) -> Tuple[str, List[dict]]:
        """
        Extract keywords from text with automatic language detection.

        Args:
            text: The text to extract keywords from.
            lang: Optional language code override. If None, auto-detected.

        Returns:
            Tuple of (detected_language, list_of_keyword_dicts)
        """
        if not text or not text.strip():
            return ('en', [])

        if lang is None:
            lang = detect_language(text)

        # For English, delegate to the main extractor (which has skills DB + entity ruler)
        if lang == 'en':
            from .keyword_extractor import SpaCyKeywordExtractor
            extractor = SpaCyKeywordExtractor(max_keywords=self.max_keywords)
            return ('en', extractor.extract_keywords(text))

        # For other languages, use the language-specific model
        nlp = load_model(lang)
        if nlp is None:
            # Fallback to English extractor
            from .keyword_extractor import SpaCyKeywordExtractor
            extractor = SpaCyKeywordExtractor(max_keywords=self.max_keywords)
            return (lang, extractor.extract_keywords(text))

        doc = nlp(text)
        keywords = {}

        # Extract named entities
        for ent in doc.ents:
            key = ent.text.strip().lower()
            if len(key) > 2 and ent.label_ in (
                'ORG', 'PRODUCT', 'GPE', 'SKILL', 'MISC', 'PER', 'LOC',
            ):
                keywords[key] = keywords.get(key, 0) + 1

        # Extract noun phrases
        try:
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip().lower()
                if 2 < len(phrase) < 50 and len(phrase.split()) <= 4:
                    keywords[phrase] = keywords.get(phrase, 0) + 1
        except (NotImplementedError, AttributeError):
            # Some models don't support noun_chunks
            pass

        # Format results
        results = []
        max_count = max(keywords.values()) if keywords else 1
        for kw, count in keywords.items():
            if count >= max(2, max_count * 0.3):
                importance = 'high'
            elif count >= 2:
                importance = 'medium'
            else:
                importance = 'low'

            results.append({
                'keyword': kw,
                'count': count,
                'importance': importance,
                'category': 'general',
            })

        importance_order = {'high': 0, 'medium': 1, 'low': 2}
        results.sort(key=lambda r: (importance_order[r['importance']], -r['count']))
        return (lang, results[:self.max_keywords])


def get_supported_languages() -> List[dict]:
    """Return list of supported languages with install status."""
    import importlib
    languages = []
    for lang, models in LANGUAGE_MODELS.items():
        if lang == 'xx':
            continue
        installed = False
        installed_model = None
        for model_name in models:
            try:
                importlib.import_module(model_name.replace('-', '_'))
                installed = True
                installed_model = model_name
                break
            except ImportError:
                try:
                    import spacy
                    spacy.load(model_name)
                    installed = True
                    installed_model = model_name
                    break
                except Exception:
                    continue

        lang_names = {
            'en': 'English', 'fr': 'French', 'de': 'German',
            'es': 'Spanish', 'hi': 'Hindi', 'zh': 'Chinese',
            'ja': 'Japanese',
        }

        languages.append({
            'code': lang,
            'name': lang_names.get(lang, lang),
            'installed': installed,
            'model': installed_model or models[0],
            'install_command': f"python -m spacy download {models[0]}",
        })

    return languages
