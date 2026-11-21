"""Runs privileged CLI commands (apply/reset) asynchronously through QProcess + pkexec."""

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

logger = logging.getLogger(__name__)

# pkexec exit codes when the user dismisses or fails the authentication dialog.
_AUTH_CANCELLED_CODES = (126, 127)


class PrivilegedHelper(QObject):
    """Starts ``python -m routepilot <command>``; the CLI elevates itself via pkexec.

    Requests arriving while a run is in progress are coalesced into one follow-up run, so
    rapid toggling never queues several authentication prompts.
    """

    busy_changed = pyqtSignal(bool)
    # command, success, message (stderr/stdout tail or empty)
    finished = pyqtSignal(str, bool, str)
    auth_cancelled = pyqtSignal(str)

    def __init__(self, policy_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.policy_path = policy_path
        self._process: QProcess | None = None
        self._pending: str | None = None
        self._command = ""

    @property
    def is_busy(self) -> bool:
        return self._process is not None

    def apply_policy(self) -> None:
        self._request("apply")

    def reset_state(self) -> None:
        self._request("reset")

    def command_for(self, command: str) -> list[str]:
        """Full argv used for ``command`` (exposed for tests and logging)."""
        return [sys.executable, "-m", "routepilot", "--policy", str(self.policy_path), command]

    def _request(self, command: str) -> None:
        if self._process is not None:
            self._pending = command
            return
        self._start(command)

    def _start(self, command: str) -> None:
        argv = self.command_for(command)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)
        self._process, self._command = process, command
        logger.info("Running privileged helper: %s", " ".join(argv))
        self.busy_changed.emit(True)
        process.start(argv[0], argv[1:])

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._complete(False, "RoutePilot helper could not be started.")

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        output = ""
        if self._process is not None:
            output = bytes(self._process.readAllStandardOutput().data()).decode(errors="replace")
        if exit_code in _AUTH_CANCELLED_CODES:
            self.auth_cancelled.emit(self._command)
            self._complete(None, "")
            return
        lines = [line for line in output.strip().splitlines() if line.strip()]
        error_lines = [line for line in lines if line.lower().startswith(("error", "warning"))]
        message = (error_lines or lines or [""])[-1]
        self._complete(exit_code == 0, message)

    def _complete(self, success: bool | None, message: str) -> None:
        command = self._command
        if self._process is not None:
            self._process.deleteLater()
        self._process = None
        if success is not None:
            self.finished.emit(command, success, message)
        if self._pending:
            pending, self._pending = self._pending, None
            self._start(pending)
        else:
            self.busy_changed.emit(False)
