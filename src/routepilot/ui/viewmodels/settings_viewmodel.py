"""ViewModel for Application Settings and maintenance actions."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort
from routepilot.ui.translation_manager import TranslationManager


class SettingsViewModel(QObject):
    """ViewModel managing user settings, theme selection, language, and emergency maintenance."""

    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    reset_completed = pyqtSignal(str)

    def __init__(
        self, policy_repo: PolicyRepositoryPort, reconciliation_service: ReconciliationService
    ) -> None:
        super().__init__()
        self._policy_repo = policy_repo
        self._reconciliation = reconciliation_service
        self._current_theme = "dark"
        self._i18n = TranslationManager.instance()
        self._i18n.language_changed.connect(self.language_changed.emit)

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @property
    def current_language(self) -> str:
        return self._i18n.current_language

    def set_theme(self, theme_name: str) -> None:
        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)

    def set_language(self, lang_code: str) -> None:
        """Updates UI language and notifies listeners."""
        self._i18n.set_language(lang_code)

    def trigger_emergency_reset(self) -> None:
        """Executes full emergency purge of RoutePilot kernel state."""
        self._reconciliation.emergency_reset()
        self.reset_completed.emit("RoutePilot tables, rules, and transient state were purged.")

    def clear_all_rules(self) -> None:
        """Empties all configured routing rules."""
        doc = PolicyDocument(schema_version=1, updated_at="", rules=[])
        self._policy_repo.save_policy(doc)
        self.reset_completed.emit("All configured rules have been cleared.")
