"""ViewModel for Application Settings and maintenance actions."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort


class SettingsViewModel(QObject):
    """ViewModel managing user settings, theme selection, and emergency maintenance."""

    theme_changed = pyqtSignal(str)
    reset_completed = pyqtSignal(str)

    def __init__(
        self, policy_repo: PolicyRepositoryPort, reconciliation_service: ReconciliationService
    ) -> None:
        super().__init__()
        self._policy_repo = policy_repo
        self._reconciliation = reconciliation_service
        self._current_theme = "dark"

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)

    def trigger_emergency_reset(self) -> None:
        """Executes full emergency purge of RoutePilot kernel state."""
        self._reconciliation.emergency_reset()
        self.reset_completed.emit("RoutePilot tables, rules, and transient state were purged.")

    def clear_all_rules(self) -> None:
        """Empties all configured routing rules."""
        doc = PolicyDocument(schema_version=1, updated_at="", rules=[])
        self._policy_repo.save_policy(doc)
        self.reset_completed.emit("All configured rules have been cleared.")
