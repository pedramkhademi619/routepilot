"""Runs the real kernel adapters inside an unprivileged, disposable network namespace."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCENARIO = Path(__file__).with_name("netns_scenario.py")


def _netns_available() -> bool:
    if not all(shutil.which(tool) for tool in ("unshare", "ip", "nft")):
        return False
    probe = subprocess.run(
        ["unshare", "-rn", "ip", "link", "add", "probe0", "type", "dummy"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


@pytest.mark.skipif(not _netns_available(), reason="unprivileged network namespaces unavailable")
def test_kernel_scenario_in_network_namespace() -> None:
    proc = subprocess.run(
        ["unshare", "-rn", sys.executable, str(SCENARIO)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"ok": true' in proc.stdout
