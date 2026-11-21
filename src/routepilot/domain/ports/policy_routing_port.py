"""Port interface for Linux kernel routing policy database (RPDB)."""

from abc import ABC, abstractmethod

from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.models.rpdb_rule import RpdbRule


class PolicyRoutingPort(ABC):
    """Port interface for managing Linux routing tables and ip rules."""

    @abstractmethod
    def replace_route(self, route: RouteEntry) -> None:
        """Adds the route, or replaces an existing route with the same table/destination."""

    @abstractmethod
    def delete_route(self, route: RouteEntry) -> None:
        """Deletes a route; deleting a route that does not exist is not an error."""

    @abstractmethod
    def list_routes(self, table_id: int, family: int = 4) -> list[RouteEntry]:
        """Lists all routes currently configured in the given table."""

    @abstractmethod
    def flush_table(self, table_id: int, family: int = 4) -> None:
        """Deletes every route inside the given table."""

    @abstractmethod
    def replace_rule(self, rule: RpdbRule) -> None:
        """Makes ``rule`` the only ip rule at its priority (idempotent)."""

    @abstractmethod
    def delete_rule(self, priority: int, family: int = 4) -> None:
        """Deletes all ip rules at ``priority``; missing rules are not an error."""
