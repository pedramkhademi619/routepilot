"""Policy action specification model."""

from pydantic import BaseModel, Field

from routepilot.domain.policy.action_type import ActionType


class PolicyAction(BaseModel):
    """Action specification for matched traffic."""

    type: ActionType = Field(..., description="Action classification")
    target_connection_uuid: str | None = Field(
        default=None,
        description="Target connection UUID when type is USE_DIRECT or USE_SELECTED_VPN",
    )
    excluded_vpn_uuids: list[str] = Field(
        default_factory=list, description="List of VPN UUIDs to exclude when type is EXCLUDE_VPN"
    )
