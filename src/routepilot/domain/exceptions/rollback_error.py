"""Rollback execution error."""

from routepilot.domain.exceptions.routepilot_error import RoutePilotError


class RollbackError(RoutePilotError):
    """Raised when a staged application fails and automatic rollback fails."""
