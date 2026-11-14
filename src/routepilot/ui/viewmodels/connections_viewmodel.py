"""ViewModel for the Connections screen."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.domain.models.network_connection import NetworkConnection


class ConnectionsViewModel(QObject):
    """ViewModel presenting active network adapters and VPNs with technical capability details."""

    connections_updated = pyqtSignal()

    def __init__(self, discovery_service: DiscoveryService) -> None:
        super().__init__()
        self._discovery_service = discovery_service
        self._discovery_service.add_change_listener(self._on_change)

    def refresh(self) -> None:
        self.connections_updated.emit()

    @property
    def connections(self) -> list[NetworkConnection]:
        return self._discovery_service.get_cached_connections()

    def _on_change(self, conns: list[NetworkConnection]) -> None:
        self.connections_updated.emit()
