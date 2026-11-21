"""ViewModel for the Overview screen."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort


class OverviewViewModel(QObject):
    """ViewModel providing aggregated data for the RoutePilot Overview screen."""

    data_changed = pyqtSignal()

    def __init__(
        self, discovery_service: DiscoveryService, policy_repo: PolicyRepositoryPort
    ) -> None:
        super().__init__()
        self._discovery_service = discovery_service
        self._policy_repo = policy_repo
        self._discovery_service.add_change_listener(self._on_connections_changed)

    def refresh(self) -> None:
        """Triggers an update signal to all bound views."""
        self.data_changed.emit()

    @property
    def active_vpns(self) -> list[NetworkConnection]:
        return self._discovery_service.get_active_vpns()

    @property
    def direct_connection(self) -> NetworkConnection | None:
        return self._discovery_service.get_direct_connection()

    def rule_counts(self) -> tuple[int, int]:
        """(enabled rules, total rules)."""
        rules = self._policy_repo.load_policy().rules
        return sum(1 for r in rules if r.enabled), len(rules)

    @property
    def state_key(self) -> str:
        """Translation key describing the overall connectivity state."""
        has_vpn, direct = bool(self.active_vpns), self.direct_connection
        if direct and has_vpn:
            return "overview.state.vpn_and_direct"
        if direct:
            return "overview.state.direct_only"
        if has_vpn:
            return "overview.state.vpn_only"
        return "overview.state.offline"

    def _on_connections_changed(self, _conns: list[NetworkConnection]) -> None:
        self.data_changed.emit()
