"""Rule conflict error."""

from routepilot.domain.exceptions.routepilot_error import RoutePilotError


class RuleConflictError(RoutePilotError):
    """Raised when two or more active routing rules have unresolvable conflicts."""

    def __init__(self, rule_id_a: str, rule_id_b: str, reason: str) -> None:
        super().__init__(f"Rule conflict between '{rule_id_a}' and '{rule_id_b}': {reason}")
        self.rule_id_a = rule_id_a
        self.rule_id_b = rule_id_b
        self.reason = reason
