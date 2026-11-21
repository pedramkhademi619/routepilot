"""Activation condition model."""

from collections.abc import Iterable

from pydantic import BaseModel, Field

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.condition_type import ConditionType


class ActivationCondition(BaseModel):
    """Activation condition governing when a rule takes effect."""

    type: ConditionType = Field(default=ConditionType.ALWAYS, description="Condition type")
    target_vpn_uuid: str | None = Field(
        default=None, description="Target VPN connection UUID when type is SPECIFIC_VPN_ACTIVE"
    )
    target_profile_name: str | None = Field(
        default=None, description="Profile name when type is NETWORK_PROFILE_ACTIVE"
    )

    def is_satisfied(self, connections: Iterable[NetworkConnection]) -> bool:
        """Returns True when the rule should be enforced for the given live connections."""
        active = [c for c in connections if c.is_active]
        if self.type == ConditionType.ANY_VPN_ACTIVE:
            return any(c.is_vpn for c in active)
        if self.type == ConditionType.SPECIFIC_VPN_ACTIVE:
            return self.target_vpn_uuid is not None and any(
                c.is_vpn and c.uuid == self.target_vpn_uuid for c in active
            )
        if self.type == ConditionType.NETWORK_PROFILE_ACTIVE:
            return self.target_profile_name is not None and any(
                self.target_profile_name in (c.id, c.uuid) for c in active
            )
        return True
