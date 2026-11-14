"""Routing rule domain entity."""

import uuid

from pydantic import BaseModel, Field

from routepilot.domain.policy.activation_condition import ActivationCondition
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.traffic_selector import TrafficSelector


class RoutingRule(BaseModel):
    """Complete typed routing policy rule entity."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Stable unique rule ID")
    name: str = Field(..., description="Human-readable rule name")
    description: str | None = Field(default=None, description="Optional user note")
    enabled: bool = Field(default=True, description="Whether rule is currently active")
    priority: int = Field(
        default=100, ge=1, le=9999, description="Rule priority (lower number = higher priority)"
    )
    selector: TrafficSelector = Field(..., description="Traffic selector")
    condition: ActivationCondition = Field(
        default_factory=ActivationCondition, description="Activation condition"
    )
    action: PolicyAction = Field(..., description="Egress routing action")
    fallback: FallbackPolicy = Field(
        default_factory=FallbackPolicy, description="Fallback policy on disconnect"
    )

    def human_summary(self) -> str:
        """Returns a clear, plain-language description of the rule."""
        sel = f"{self.selector.type.value} '{self.selector.value}'"
        act = self.action.type.value.replace("_", " ")

        cond = ""
        if self.condition.type == ConditionType.ALWAYS:
            cond = "at all times"
        elif self.condition.type == ConditionType.ANY_VPN_ACTIVE:
            cond = "whenever any VPN is connected"
        elif self.condition.type == ConditionType.SPECIFIC_VPN_ACTIVE:
            cond = f"when VPN {self.condition.target_vpn_uuid or 'selected'} is connected"

        fail = (
            "blocks traffic"
            if self.fallback.behavior == FailureBehavior.BLOCK
            else "falls back to default"
        )

        return f"Route {sel} to {act} ({cond}). If unavailable, {fail}."
