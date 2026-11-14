"""ViewModel for the Overview screen."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.policy_document import PolicyDocument
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
    def connections(self) -> list[NetworkConnection]:
        return self._discovery_service.get_cached_connections()

    @property
    def active_vpns(self) -> list[NetworkConnection]:
        return self._discovery_service.get_active_vpns()

    @property
    def direct_connection(self) -> NetworkConnection | None:
        return self._discovery_service.get_direct_connection()

    @property
    def policy_document(self) -> PolicyDocument:
        return self._policy_repo.load_policy()

    @property
    def active_rules_count(self) -> int:
        return sum(1 for r in self.policy_document.rules if r.enabled)

    @property
    def total_rules_count(self) -> int:
        return len(self.policy_document.rules)

    @property
    def status_summary(self) -> str:
        vpns = len(self.active_vpns)
        direct = self.direct_connection
        if direct and vpns > 0:
            return f"Active ({vpns} VPN connected, direct bypass via {direct.interface})"
        elif direct:
            return f"Connected to {direct.id} ({direct.interface}) — No VPN active"
        elif vpns > 0:
            return f"VPN active ({vpns} connected) — No direct physical egress detected"
        return "Offline / No active network connections"

    def _on_connections_changed(self, conns: list[NetworkConnection]) -> None:
        self.data_changed.emit()
