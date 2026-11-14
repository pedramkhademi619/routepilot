"""Model representing the result of evaluating traffic against rules."""

from pydantic import BaseModel, Field

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.routing_rule import RoutingRule


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation for a destination or application."""

    matched_rule: RoutingRule | None = Field(default=None, description="Winning rule by priority")
    action: ActionType = Field(default=ActionType.FOLLOW_SYSTEM, description="Effective action")
    target_connection: NetworkConnection | None = Field(
        default=None, description="Target egress network connection if routed"
    )
    is_blocked: bool = Field(default=False, description="True if traffic must be blocked/dropped")
    explanation: str = Field(
        ..., description="Human-readable explanation of why this policy was chosen"
    )
    conflicts: list[str] = Field(
        default_factory=list, description="Any detected rule conflicts or warnings"
    )
