"""Port interface for the crash-recovery journal of applied plans."""

from abc import ABC, abstractmethod

from routepilot.domain.models.routepilot_plan import RoutePilotPlan


class PlanJournalPort(ABC):
    """Persists the last applied plan so it can be reconciled or rolled back later."""

    @abstractmethod
    def load(self) -> RoutePilotPlan | None:
        """Returns the last journaled plan, or None if nothing is applied."""

    @abstractmethod
    def save(self, plan: RoutePilotPlan, status: str) -> None:
        """Records ``plan`` with a status such as ``staged`` or ``committed``."""

    @abstractmethod
    def clear(self) -> None:
        """Forgets the journaled plan (after a full teardown)."""
