"""Translation utility function for i18n support.

Provides the `t()` function that looks up translations from
config/i18n.py TRANSLATIONS dictionary.
"""

from __future__ import annotations

from config.i18n import TRANSLATIONS


def t(key: str, lang: str = "en", **kwargs: str) -> str:
    """Translate a key to the specified language.

    Falls back to English if key not found in target language.
    Falls back to the key itself if not found in either.

    Args:
        key: Translation key (e.g., 'nav.overview').
        lang: Language code ('en' or 'pt').
        **kwargs: Format variables for string interpolation.

    Returns:
        Translated string.
    """
    translations = TRANSLATIONS.get(lang, TRANSLATIONS.get("en", {}))
    text = translations.get(key)
    if text is None:
        text = TRANSLATIONS.get("en", {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
