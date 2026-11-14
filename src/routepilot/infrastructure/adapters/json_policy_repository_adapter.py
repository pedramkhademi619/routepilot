"""JSON file persistence adapter for PolicyRepositoryPort."""

import json
import logging
import os
import tempfile
from datetime import UTC, datetime

from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort

logger = logging.getLogger(__name__)


class JsonPolicyRepositoryAdapter(PolicyRepositoryPort):
    """Persists PolicyDocument to a versioned JSON file with atomic replacement."""

    DEFAULT_CONFIG_PATH = "~/.config/routepilot/policy.json"

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = os.path.expanduser(file_path or self.DEFAULT_CONFIG_PATH)

    def load_policy(self) -> PolicyDocument:
        """Loads and parses the policy document, or returns a new empty one if not found."""
        if not os.path.exists(self.file_path):
            return PolicyDocument(
                schema_version=1,
                updated_at=datetime.now(UTC).isoformat(),
                rules=[],
            )

        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
            return PolicyDocument.model_validate(data)
        except Exception as e:
            logger.error(
                "Failed to load policy from %s: %s. Returning empty policy.", self.file_path, e
            )
            return PolicyDocument(
                schema_version=1,
                updated_at=datetime.now(UTC).isoformat(),
                rules=[],
            )

    def save_policy(self, document: PolicyDocument) -> None:
        """Atomically writes the policy document to disk using a temporary file."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        dir_name = os.path.dirname(self.file_path)

        data = document.model_dump(mode="json")
        data["updated_at"] = datetime.now(UTC).isoformat()

        # Atomic write: write to temp file then rename
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            temp_name = tf.name
            json.dump(data, tf, indent=2)

        os.replace(temp_name, self.file_path)
        logger.info("Saved policy to %s with %d rules.", self.file_path, len(document.rules))
