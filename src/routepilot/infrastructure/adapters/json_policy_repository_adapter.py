"""JSON file persistence adapter for PolicyRepositoryPort."""

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort
from routepilot.infrastructure import paths

logger = logging.getLogger(__name__)


class JsonPolicyRepositoryAdapter(PolicyRepositoryPort):
    """Persists PolicyDocument to a versioned JSON file with atomic replacement."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        self.file_path = Path(file_path).expanduser() if file_path else paths.policy_file()

    def load_policy(self) -> PolicyDocument:
        """Loads the policy document, or returns an empty one if none exists yet."""
        if not self.file_path.exists():
            return self._empty()

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            document = PolicyDocument.model_validate(data)
        except Exception as e:
            # Keep the unreadable file aside so a later save cannot destroy the user's rules.
            backup = self.file_path.with_name(
                f"{self.file_path.name}.corrupt-{datetime.now(UTC):%Y%m%dT%H%M%S}"
            )
            try:
                os.replace(self.file_path, backup)
                logger.error("Could not parse %s (%s); moved it to %s.", self.file_path, e, backup)
            except OSError as move_error:
                logger.error("Could not parse %s (%s): %s", self.file_path, e, move_error)
            return self._empty()

        if self._has_rules_without_id(data) and self._owned_by_current_user():
            # Hand-written rules get random IDs on every load; persist them once so the GUI
            # can address rules reliably. Root never rewrites the user's file.
            self.save_policy(document)
        return document

    def save_policy(self, document: PolicyDocument) -> None:
        """Atomically writes the policy document to disk using a temporary file."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = document.model_dump(mode="json")
        data["updated_at"] = datetime.now(UTC).isoformat()

        with tempfile.NamedTemporaryFile(
            "w", dir=self.file_path.parent, delete=False, encoding="utf-8"
        ) as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
        os.replace(tf.name, self.file_path)
        logger.info("Saved policy to %s with %d rules.", self.file_path, len(document.rules))

    @staticmethod
    def _has_rules_without_id(data: object) -> bool:
        rules = data.get("rules", []) if isinstance(data, dict) else []
        return any(isinstance(r, dict) and "id" not in r for r in rules)

    def _owned_by_current_user(self) -> bool:
        try:
            return self.file_path.stat().st_uid == os.geteuid()
        except OSError:
            return False

    @staticmethod
    def _empty() -> PolicyDocument:
        return PolicyDocument(schema_version=1, updated_at=datetime.now(UTC).isoformat(), rules=[])
