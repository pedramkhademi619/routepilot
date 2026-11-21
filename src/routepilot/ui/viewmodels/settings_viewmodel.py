"""ViewModel for Application Settings and maintenance actions."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from routepilot.ui.controllers.privileged_helper import PrivilegedHelper
from routepilot.ui.style import ThemeManager
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel


class SettingsViewModel(QObject):
    """ViewModel managing theme, language and emergency maintenance."""

    language_changed = pyqtSignal(str)
    theme_changed = pyqtSignal(str)

    def __init__(
        self,
        theme_manager: ThemeManager,
        rules_vm: RulesViewModel,
        helper: PrivilegedHelper,
    ) -> None:
        super().__init__()
        self._theme_manager = theme_manager
        self._rules_vm = rules_vm
        self._helper = helper
        self._i18n = TranslationManager.instance()
        self._i18n.language_changed.connect(self.language_changed.emit)

    @property
    def current_theme(self) -> str:
        return self._theme_manager.theme

    @property
    def current_language(self) -> str:
        return self._i18n.current_language

    @property
    def languages(self) -> dict[str, str]:
        return self._i18n.available_languages

    def set_theme(self, theme_name: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme_manager.set_theme(theme_name, app)
        self.theme_changed.emit(self._theme_manager.theme)

    def set_language(self, lang_code: str) -> None:
        """Updates UI language (and layout direction) and notifies listeners."""
        self._i18n.set_language(lang_code)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self._theme_manager.apply(app)  # alignment rules depend on direction

    def trigger_emergency_reset(self) -> None:
        """Asks the privileged helper to purge RoutePilot kernel state."""
        self._helper.reset_state()

    def clear_all_rules(self) -> None:
        self._rules_vm.clear_all_rules()
