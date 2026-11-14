"""Systemd cgroup v2 execution adapter implementing CgroupRunnerPort."""

import logging
import shutil
import subprocess

from routepilot.domain.ports.cgroup_runner_port import CgroupRunnerPort

logger = logging.getLogger(__name__)


class SystemdCgroupAdapter(CgroupRunnerPort):
    """Launches processes in designated systemd cgroup v2 scopes."""

    def __init__(self) -> None:
        self.systemd_run_path = shutil.which("systemd-run") or "/usr/bin/systemd-run"
        self.systemctl_path = shutil.which("systemctl") or "/usr/bin/systemctl"

    def launch_in_scope(self, scope_unit_id: str, command: list[str]) -> int:
        """Launches command in a dedicated user scope, returning process PID."""
        unit_name = f"routepilot-app-{scope_unit_id}"
        full_cmd = [
            self.systemd_run_path,
            "--user",
            "--scope",
            f"--unit={unit_name}",
            "--description=RoutePilot Managed Application Scope",
            *command,
        ]
        logger.info("Launching scope '%s': %s", unit_name, " ".join(command))
        proc = subprocess.Popen(full_cmd)
        return proc.pid

    def terminate_scope(self, scope_unit_id: str) -> None:
        """Stops the specified systemd user scope."""
        unit_name = f"routepilot-app-{scope_unit_id}.scope"
        logger.info("Stopping scope '%s'...", unit_name)
        subprocess.run(
            [self.systemctl_path, "--user", "stop", unit_name],
            capture_output=True,
            check=False,
        )
