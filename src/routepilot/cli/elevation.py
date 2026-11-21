"""Re-runs a privileged CLI command as root through polkit's pkexec."""

import os
import shutil
import subprocess
import sys


def is_root() -> bool:
    return os.geteuid() == 0


def run_elevated(cli_args: list[str]) -> int:
    """Executes ``python -m routepilot <cli_args>`` via pkexec and returns its exit code."""
    pkexec = shutil.which("pkexec")
    if not pkexec:
        print(
            "Error: root privileges are required and pkexec (polkit) is not installed.\n"
            f"Run again with sudo: sudo {sys.executable} -m routepilot {' '.join(cli_args)}",
            file=sys.stderr,
        )
        return 1
    # pkexec resets the environment; the interpreter path keeps the same installation.
    return subprocess.run([pkexec, sys.executable, "-m", "routepilot", *cli_args]).returncode
