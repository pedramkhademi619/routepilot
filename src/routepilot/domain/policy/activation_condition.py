"""Activation condition model."""

from pydantic import BaseModel, Field

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
