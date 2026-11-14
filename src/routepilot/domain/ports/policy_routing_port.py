"""Port interface for Linux kernel routing policy database (RPDB)."""

from abc import ABC, abstractmethod

from routepilot.domain.models.route_entry import RouteEntry


class PolicyRoutingPort(ABC):
    """Port interface for managing Linux routing tables and ip rules."""

    @abstractmethod
    def add_routing_table_route(self, table_id: int, route: RouteEntry) -> None:
        """Adds a route entry to a specific policy routing table."""

    @abstractmethod
    def remove_routing_table_route(self, table_id: int, destination: str, family: int = 4) -> None:
        """Removes a route entry from a policy routing table."""

    @abstractmethod
    def add_policy_rule(
        self, table_id: int, priority: int, fwmark: int, fwmask: int = 0x00FF0000, family: int = 4
    ) -> None:
        """Creates an ip rule matching fwmark pointing to table_id."""

    @abstractmethod
    def remove_policy_rule(self, priority: int, family: int = 4) -> None:
        """Deletes an ip rule at the specified priority."""

    @abstractmethod
    def flush_table_routes(self, table_id: int, family: int = 4) -> None:
        """Flushes all routes inside the designated RoutePilot policy table."""

    @abstractmethod
    def list_table_routes(self, table_id: int, family: int = 4) -> list[RouteEntry]:
        """Lists all routes currently configured in the given policy table."""
