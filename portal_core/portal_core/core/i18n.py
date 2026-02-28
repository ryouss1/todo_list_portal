"""Internationalization (i18n) utilities using Python gettext + Babel."""

import gettext
import os
from typing import Optional

from portal_core.config import DEFAULT_LOCALE, SUPPORTED_LOCALES

_translations = {}
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "translations")


def _load_translations():
    """Load translations for all supported locales at startup."""
    for locale in SUPPORTED_LOCALES:
        try:
            _translations[locale] = gettext.translation("messages", LOCALE_DIR, languages=[locale])
        except FileNotFoundError:
            _translations[locale] = gettext.NullTranslations()


def get_translator(locale: Optional[str] = None):
    """Return the translation object for the given locale."""
    if not _translations:
        _load_translations()
    loc = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    return _translations.get(loc, _translations.get(DEFAULT_LOCALE))


def translate(message: str, locale: Optional[str] = None) -> str:
    """Translate a message string for the given locale."""
    t = get_translator(locale)
    return t.gettext(message)


def reload_translations():
    """Reload all translations (useful after pybabel compile)."""
    _translations.clear()
    _load_translations()
