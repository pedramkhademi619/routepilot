"""Application translation and internationalization manager for RoutePilot."""

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

from routepilot.ui.settings_store import UiSettingsStore

logger = logging.getLogger(__name__)

CATALOG_DIR = Path(__file__).with_name("i18n")
RTL_LANGUAGES = {"fa"}
RLM = "\u200f"  # Right-to-left mark
LRI, PDI = "\u2066", "\u2069"  # Left-to-right isolate / pop directional isolate


class TranslationManager(QObject):
    """Loads JSON catalogs from ``ui/i18n`` and switches language (and direction) at runtime."""

    language_changed = pyqtSignal(str)

    _instance: "TranslationManager | None" = None

    def __init__(self, store: UiSettingsStore | None = None) -> None:
        super().__init__()
        self._store = store or UiSettingsStore()
        self.catalogs = self._load_catalogs()
        language = self._store.get("language", "en")
        self._current_language = language if language in self.catalogs else "en"

    @classmethod
    def instance(cls) -> "TranslationManager":
        """Singleton accessor for TranslationManager."""
        if cls._instance is None:
            cls._instance = TranslationManager()
        return cls._instance

    @property
    def current_language(self) -> str:
        return self._current_language

    @property
    def is_rtl(self) -> bool:
        return self._current_language in RTL_LANGUAGES

    @property
    def available_languages(self) -> dict[str, str]:
        """Language code -> native language name."""
        return {code: cat.get("language.native_name", code) for code, cat in self.catalogs.items()}

    def t(self, key: str, **kwargs: Any) -> str:
        """Translates ``key``, falling back to English and then to the key itself."""
        text = self.catalogs.get(self._current_language, {}).get(key)
        if text is None:
            text = self.catalogs.get("en", {}).get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return self._with_direction(text)

    def ltr(self, text: str) -> str:
        """Keeps inherently left-to-right values (domains, IPs) intact inside RTL text."""
        return f"{LRI}{text}{PDI}" if self.is_rtl else text

    def _with_direction(self, text: str) -> str:
        """Qt guesses paragraph direction from the first strong character, so RTL strings that
        start with a Latin word (e.g. "VPN…") would be laid out left-to-right without a mark."""
        if not self.is_rtl:
            return text
        for char in text:
            bidi = unicodedata.bidirectional(char)
            if bidi in ("R", "AL"):
                return text
            if bidi == "L":
                return RLM + text
        return text

    def set_language(self, lang: str) -> None:
        """Switches active language, sets Qt layout direction, and notifies observers."""
        if lang not in self.catalogs:
            lang = "en"
        if self._current_language == lang:
            return
        self._current_language = lang
        self._store.set("language", lang)
        self.apply_layout_direction()
        self.language_changed.emit(lang)

    def apply_layout_direction(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft if self.is_rtl else Qt.LayoutDirection.LeftToRight
            )

    @staticmethod
    def _load_catalogs() -> dict[str, dict[str, str]]:
        catalogs: dict[str, dict[str, str]] = {}
        for path in sorted(CATALOG_DIR.glob("*.json")):
            try:
                catalogs[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                logger.error("Broken translation catalog %s: %s", path, e)
        return catalogs
