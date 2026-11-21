"""Unit tests for TranslationManager catalogs, fallback logic and persistence."""

import json
from pathlib import Path

from routepilot.ui.settings_store import UiSettingsStore
from routepilot.ui.translation_manager import CATALOG_DIR, TranslationManager


def test_catalogs_define_the_same_keys() -> None:
    catalogs = {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in CATALOG_DIR.glob("*.json")
    }
    assert {"en", "fa"} <= set(catalogs)
    english = set(catalogs["en"])
    for lang, catalog in catalogs.items():
        assert set(catalog) == english, f"{lang}: {set(catalog) ^ english}"


def test_placeholders_match_between_languages() -> None:
    import string

    def fields(text: str) -> set[str]:
        return {name for _, name, _, _ in string.Formatter().parse(text) if name}

    en = json.loads((CATALOG_DIR / "en.json").read_text(encoding="utf-8"))
    fa = json.loads((CATALOG_DIR / "fa.json").read_text(encoding="utf-8"))
    for key, text in en.items():
        assert fields(text) == fields(fa[key]), key


def test_translation_and_fallbacks(tmp_path: Path) -> None:
    i18n = TranslationManager(UiSettingsStore(tmp_path / "settings.json"))
    assert i18n.t("nav.rules") == "Traffic Rules"
    assert i18n.t("non_existent_key_123") == "non_existent_key_123"
    assert i18n.t("overview.stat_rules_value", active=2, total=5) == "2 of 5"


def test_language_switch_is_persisted(tmp_path: Path) -> None:
    store = UiSettingsStore(tmp_path / "settings.json")
    i18n = TranslationManager(store)
    i18n.set_language("fa")
    assert i18n.is_rtl
    assert i18n.t("nav.settings") == "تنظیمات"
    assert TranslationManager(store).current_language == "fa"

    i18n.set_language("xx")  # unknown -> English
    assert i18n.current_language == "en"
