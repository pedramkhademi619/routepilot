"""Kernel route type enum."""

from enum import StrEnum


class RouteType(StrEnum):
    """Subset of Linux route types RoutePilot installs in its own tables."""

    UNICAST = "unicast"  # Forward via a gateway and/or interface
    UNREACHABLE = "unreachable"  # Fail fast with EHOSTUNREACH (fail-closed guard)
    THROW = "throw"  # Stop looking in this table and continue with the next ip rule
