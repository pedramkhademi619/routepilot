"""JSON file adapter for PlanJournalPort."""

import json
import logging
import os
import tempfile
from pathlib import Path

from routepilot.domain.models.routepilot_plan import RoutePilotPlan
from routepilot.domain.ports.plan_journal_port import PlanJournalPort
from routepilot.infrastructure import paths

logger = logging.getLogger(__name__)


class JsonPlanJournalAdapter(PlanJournalPort):
    """Stores the last applied plan as JSON, written atomically."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path = Path(file_path) if file_path else paths.runtime_dir() / "journal.json"

    def load(self) -> RoutePilotPlan | None:
        if not self.file_path.exists():
            return None
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return RoutePilotPlan.model_validate(data["plan"])
        except Exception as e:
            # A journal from an older RoutePilot version: teardown still covers its state.
            logger.warning("Ignoring unreadable journal %s: %s", self.file_path, e)
            return None

    def save(self, plan: RoutePilotPlan, status: str) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"status": status, "plan": plan.model_dump(mode="json")}
        with tempfile.NamedTemporaryFile(
            "w", dir=self.file_path.parent, delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(payload, tmp, indent=2)
        os.replace(tmp.name, self.file_path)

    def clear(self) -> None:
        self.file_path.unlink(missing_ok=True)
