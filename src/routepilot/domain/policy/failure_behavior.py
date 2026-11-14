"""Failure behavior enum."""

from enum import StrEnum


class FailureBehavior(StrEnum):
    """Policy behavior when the specified egress path is disconnected/unavailable."""

    BLOCK = "block"  # Fail-closed (safest)
    FOLLOW_SYSTEM = "follow_system"  # Fail-open (requires explicit user consent)
    USE_ALTERNATIVE = "use_alternative"
