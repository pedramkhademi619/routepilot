"""Versioned persistent policy document."""

from pydantic import BaseModel, Field

from routepilot.domain.policy.routing_rule import RoutingRule


class PolicyDocument(BaseModel):
    """Versioned persistent policy collection."""

    schema_version: int = Field(default=1, description="Policy storage schema version")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    rules: list[RoutingRule] = Field(default_factory=list, description="List of configured rules")

    def sort_by_priority(self) -> list[RoutingRule]:
        """Returns rules ordered deterministically by priority ascending (1 = highest)."""
        return sorted(self.rules, key=lambda r: (r.priority, r.id))
