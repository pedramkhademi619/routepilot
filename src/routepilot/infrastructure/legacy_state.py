"""One-time cleanup of kernel state left behind by RoutePilot 0.1.x."""

import json
import logging
import os
from pathlib import Path

from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

logger = logging.getLogger(__name__)

# 0.1.x installed bypass host routes in the main table and remembered them here.
LEGACY_STATE_FILE = Path("/tmp/routepilot_active_bypass_ips.json")


def remove_legacy_host_routes(
    routing_port: PolicyRoutingPort, state_file: Path = LEGACY_STATE_FILE
) -> int:
    """Deletes main-table host routes recorded by 0.1.x; returns how many were removed."""
    try:
        info = os.lstat(state_file)
    except FileNotFoundError:
        return 0
    # Only trust a regular file written by root (the old helper ran as root).
    if not state_file.is_file() or state_file.is_symlink() or info.st_uid != 0:
        logger.warning("Ignoring untrusted legacy state file %s", state_file)
        return 0

    removed = 0
    try:
        addresses = json.loads(state_file.read_text(encoding="utf-8"))
        for address in addresses:
            routing_port.delete_route(RouteEntry(destination=str(address), table_id=254))
            removed += 1
    except Exception as e:
        logger.warning("Legacy route cleanup incomplete: %s", e)
    state_file.unlink(missing_ok=True)
    logger.info("Removed %d legacy bypass routes from the main table.", removed)
    return removed
