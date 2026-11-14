"""Mock network discovery adapter for testing and offline demo modes."""

from collections.abc import Callable

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort


class MockDiscoveryAdapter(NetworkDiscoveryPort):
    """Mock discovery adapter providing controlled network connection topologies."""

    def __init__(self, initial_connections: list[NetworkConnection] | None = None) -> None:
        self._connections: list[NetworkConnection] = (
            initial_connections
            if initial_connections is not None
            else self._default_mock_connections()
        )
        self._callbacks: list[Callable[[list[NetworkConnection]], None]] = []

    async def discover_connections(self) -> list[NetworkConnection]:
        return list(self._connections)

    async def get_active_routes(self) -> list[RouteEntry]:
        return [
            RouteEntry(
                destination="0.0.0.0/0",
                gateway="10.8.0.1",
                interface="vpn0",
                metric=50,
                table_id=254,
            ),
            RouteEntry(
                destination="0.0.0.0/0",
                gateway="192.168.1.1",
                interface="wlo1",
                metric=600,
                table_id=254,
            ),
        ]

    def subscribe_connection_changes(
        self, callback: Callable[[list[NetworkConnection]], None]
    ) -> None:
        self._callbacks.append(callback)

    def simulate_connection_change(self, new_connections: list[NetworkConnection]) -> None:
        """Simulates a live connection event."""
        self._connections = list(new_connections)
        for cb in self._callbacks:
            cb(list(self._connections))

    def _default_mock_connections(self) -> list[NetworkConnection]:
        return [
            NetworkConnection(
                id="Home-WiFi",
                uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
                interface="wlo1",
                kind=ConnectionKind.PHYSICAL_WIFI,
                is_vpn=False,
                is_default=False,
                state=ConnectionState.ACTIVATED,
                ip4_config=IPConfig(
                    addresses=["192.168.1.173/24"],
                    gateway="192.168.1.1",
                    dns_servers=["192.168.1.1"],
                    domains=["local"],
                ),
                metric=600,
            ),
            NetworkConnection(
                id="Work-VPN",
                uuid="a3b4c5d6-7e8f-4a1b-8c2d-3e4f5a6b7c8d",
                interface="vpn0",
                kind=ConnectionKind.VPN_GENERIC,
                is_vpn=True,
                is_default=True,
                state=ConnectionState.ACTIVATED,
                ip4_config=IPConfig(
                    addresses=["10.8.0.4/24"],
                    gateway="10.8.0.1",
                    dns_servers=["1.1.1.1", "1.0.0.1"],
                ),
                metric=50,
                server_endpoint="203.0.113.50",
            ),
        ]
