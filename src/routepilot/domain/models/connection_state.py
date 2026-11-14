"""Connection lifecycle state enum."""

from enum import StrEnum


class ConnectionState(StrEnum):
    """Operational lifecycle state of a connection."""

    ACTIVATED = "activated"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    DEACTIVATED = "deactivated"
    DISCONNECTED = "disconnected"
    UNMANAGED = "unmanaged"
