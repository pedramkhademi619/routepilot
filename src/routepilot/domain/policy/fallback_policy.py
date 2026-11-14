"""Fallback policy model."""

from pydantic import BaseModel, Field

from routepilot.domain.policy.failure_behavior import FailureBehavior


class FallbackPolicy(BaseModel):
    """Defines failure behavior when required egress route is missing."""

    behavior: FailureBehavior = Field(
        default=FailureBehavior.BLOCK,
        description="Failure behavior: block (fail-closed) or follow_system",
    )
    alternative_connection_uuid: str | None = Field(
        default=None,
        description="Alternative fallback connection UUID if behavior is USE_ALTERNATIVE",
    )
    user_consented_fail_open: bool = Field(
        default=False,
        description="Must be True if behavior is FOLLOW_SYSTEM to prevent accidental leaks",
    )
