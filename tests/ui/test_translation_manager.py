"""Unit tests for TranslationManager localization and fallback logic."""

from routepilot.ui.translation_manager import TranslationManager


class TestTranslationManager:
    """Verifies i18n key translation, language switching, and persistence handling."""

    def test_default_translations_and_fallbacks(self) -> None:
        i18n = TranslationManager.instance()
        i18n.set_language("en")

        assert i18n.t("common.active") == "Active"
        assert i18n.t("nav.rules") == "Traffic Rules"
        # Fallback for non-existent key returns key itself
        assert i18n.t("non_existent_key_123") == "non_existent_key_123"

    def test_persian_translations(self) -> None:
        i18n = TranslationManager.instance()
        i18n.set_language("fa")

        assert i18n.current_language == "fa"
        assert i18n.t("common.active") == "فعال"
        assert i18n.t("common.disabled") == "غیرفعال"
        assert i18n.t("nav.rules") == "قوانین ترافیک"
        assert i18n.t("nav.settings") == "تنظیمات"

        # Reset back to English
        i18n.set_language("en")
        assert i18n.current_language == "en"
