"""Domain validation error."""

from typing import Any

from routepilot.domain.exceptions.routepilot_error import RoutePilotError


class ValidationError(RoutePilotError):
    """Raised when an entity or configuration fails domain validation."""

    def __init__(self, field: str, message: str, invalid_value: Any = None) -> None:
        super().__init__(f"Validation failed for '{field}': {message}")
        self.field = field
        self.message = message
        self.invalid_value = invalid_value
