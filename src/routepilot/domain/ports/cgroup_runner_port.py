"""Port interface for cgroup v2 application execution."""

from abc import ABC, abstractmethod


class CgroupRunnerPort(ABC):
    """Port interface for launching processes in systemd cgroup v2 scopes."""

    @abstractmethod
    def launch_in_scope(self, scope_unit_id: str, command: list[str]) -> int:
        """Launches a command wrapped in a systemd user scope, returning the PID."""

    @abstractmethod
    def terminate_scope(self, scope_unit_id: str) -> None:
        """Stops the specified systemd scope and terminates child processes."""
