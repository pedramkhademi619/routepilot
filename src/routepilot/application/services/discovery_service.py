"""Discovery application service orchestrating network discovery adapters."""

import logging
from collections.abc import Callable

from routepilot.application.services.egress_resolver import EgressResolver
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Orchestrates live network connection discovery and state subscription."""

    def __init__(self, discovery_port: NetworkDiscoveryPort) -> None:
        self._discovery_port = discovery_port
        self._cached_connections: list[NetworkConnection] = []
        self._cached_routes: list[RouteEntry] = []
        self._listeners: list[Callable[[list[NetworkConnection]], None]] = []
        self._discovery_port.subscribe_connection_changes(self._on_connection_change)

    async def refresh(self) -> list[NetworkConnection]:
        """Performs a full discovery query and updates cache."""
        conns = await self._discovery_port.discover_connections()
        self._cached_connections = conns
        try:
            self._cached_routes = await self._discovery_port.get_active_routes()
        except Exception:
            self._cached_routes = []
        self._notify_listeners()
        return conns

    def get_cached_connections(self) -> list[NetworkConnection]:
        """Returns the current snapshot of active connections."""
        return list(self._cached_connections)

    def get_active_vpns(self) -> list[NetworkConnection]:
        """Returns only the currently active VPN connections."""
        return [c for c in self._cached_connections if c.is_vpn and c.is_active]

    def get_direct_connection(self) -> NetworkConnection | None:
        """Returns the primary physical non-VPN internet connection."""
        return EgressResolver().direct_connection(self._cached_connections)

    def add_change_listener(self, listener: Callable[[list[NetworkConnection]], None]) -> None:
        """Registers a listener callback for connection changes."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_change_listener(self, listener: Callable[[list[NetworkConnection]], None]) -> None:
        """Unregisters a listener callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _on_connection_change(self, updated_connections: list[NetworkConnection]) -> None:
        self._cached_connections = updated_connections
        self._notify_listeners()

    def _notify_listeners(self) -> None:
        for listener in self._listeners:
            try:
                listener(list(self._cached_connections))
            except Exception:
                logger.exception("Connection change listener failed")
