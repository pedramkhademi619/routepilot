"""Staged execution plan model for safe application and rollback."""

import uuid

from pydantic import BaseModel, Field

from routepilot.domain.models.route_entry import RouteEntry


class RoutePilotPlan(BaseModel):
    """Immutable compiled execution plan describing kernel changes."""

    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique plan ID")
    created_at: str = Field(..., description="Timestamp of plan generation")
    tables_to_create: dict[int, RouteEntry] = Field(
        default_factory=dict, description="Routing tables and default egress routes to populate"
    )
    rules_to_add: list[dict[str, int]] = Field(
        default_factory=list, description="RPDB rules to install: priority, mark, table_id, family"
    )
    nft_ruleset_content: str = Field(
        ..., description="Self-contained nftables ruleset fragment for table inet routepilot"
    )
    split_dns_links: dict[str, list[str]] = Field(
        default_factory=dict, description="Split DNS routing domains to configure per link"
    )
    summary_lines: list[str] = Field(
        default_factory=list, description="Human-readable summary of actions in this plan"
    )
    rollback_tables: list[int] = Field(
        default_factory=list, description="Table IDs to flush on rollback"
    )
    rollback_rule_priorities: list[int] = Field(
        default_factory=list, description="RPDB priorities to remove on rollback"
    )
