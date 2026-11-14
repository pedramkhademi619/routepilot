"""Target unavailable error."""

from routepilot.domain.exceptions.routepilot_error import RoutePilotError


class TargetUnavailableError(RoutePilotError):
    """Raised when an action targets a network connection or VPN that is unavailable."""

    def __init__(self, target_id: str, reason: str) -> None:
        super().__init__(f"Target '{target_id}' is unavailable: {reason}")
        self.target_id = target_id
        self.reason = reason
