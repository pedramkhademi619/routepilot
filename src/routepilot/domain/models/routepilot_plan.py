"""Compiled execution plan describing the kernel state RoutePilot should own."""

import uuid

from pydantic import BaseModel, Field

from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.models.rpdb_rule import RpdbRule


class RoutePilotPlan(BaseModel):
    """Declarative desired state: routes, ip rules, nftables table and split DNS."""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique plan ID")
    created_at: str = Field(..., description="Timestamp of plan generation")
    routes: list[RouteEntry] = Field(
        default_factory=list, description="Routes to install in RoutePilot-owned tables"
    )
    rules: list[RpdbRule] = Field(
        default_factory=list, description="ip rules pointing lookups at RoutePilot-owned tables"
    )
    nft_ruleset: str | None = Field(
        default=None, description="Ruleset for table inet routepilot, or None if not needed"
    )
    split_dns: dict[str, list[str]] = Field(
        default_factory=dict, description="Routing domains (~domain) to configure per link"
    )
    summary_lines: list[str] = Field(
        default_factory=list, description="Human-readable summary of actions in this plan"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Rules that could not be (fully) enforced and why"
    )

    def routes_in(self, table_id: int, family: int) -> list[RouteEntry]:
        """Returns the planned routes for one table and address family."""
        return [r for r in self.routes if r.table_id == table_id and r.family == family]
