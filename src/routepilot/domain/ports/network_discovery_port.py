"""Port interface for network connection discovery."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry


class NetworkDiscoveryPort(ABC):
    """Port interface for discovering active system connections and routes."""

    @abstractmethod
    async def discover_connections(self) -> list[NetworkConnection]:
        """Discovers all active and known network and VPN connections."""

    @abstractmethod
    async def get_active_routes(self) -> list[RouteEntry]:
        """Queries the kernel routing tables for active routes."""

    @abstractmethod
    def subscribe_connection_changes(
        self, callback: Callable[[list[NetworkConnection]], None]
    ) -> None:
        """Subscribes a callback to live network connection state change events."""
