"""Persistence of desktop UI preferences (language, theme)."""

import json
import logging
from pathlib import Path
from typing import Any

from routepilot.infrastructure import paths

logger = logging.getLogger(__name__)


class UiSettingsStore:
    """Small JSON key/value store at ``~/.config/routepilot/settings.json``."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or paths.settings_file()

    def get(self, key: str, default: str) -> str:
        return str(self._read().get(key, default))

    def set(self, key: str, value: str) -> None:
        data = self._read()
        data[key] = value
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("Could not save UI setting %s: %s", key, e)

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as e:
            logger.warning("Ignoring unreadable UI settings %s: %s", self.file_path, e)
            return {}
        return data if isinstance(data, dict) else {}
