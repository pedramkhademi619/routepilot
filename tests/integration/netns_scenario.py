"""Kernel scenario executed inside a throwaway network namespace (``unshare -rn``).

Builds a fake "Wi-Fi + full-tunnel VPN" topology with dummy interfaces, applies real plans
through the real pyroute2/nftables adapters and checks the kernel's routing decisions.
Never run this directly on a host network namespace.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parents[2] / "src"), str(Path(__file__).parents[1])]

from factories import VPN_UUID, rule, vpn, wifi  # noqa: E402

from routepilot.application.services.plan_compiler import PlanCompiler  # noqa: E402
from routepilot.application.services.reconciliation_service import (  # noqa: E402
    ReconciliationService,
)
from routepilot.application.services.routing_layout import RoutingLayout  # noqa: E402
from routepilot.domain.policy.action_type import ActionType  # noqa: E402
from routepilot.infrastructure.adapters.json_plan_journal_adapter import (  # noqa: E402
    JsonPlanJournalAdapter,
)
from routepilot.infrastructure.adapters.nftables_firewall_adapter import (  # noqa: E402
    NftablesFirewallAdapter,
)
from routepilot.infrastructure.adapters.pyroute2_routing_adapter import (  # noqa: E402
    Pyroute2RoutingAdapter,
)


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def route_get(address: str) -> str:
    proc = subprocess.run(["ip", "route", "get", address], capture_output=True, text=True)
    return (proc.stdout + proc.stderr).strip()


def setup_topology() -> None:
    sh("ip", "link", "set", "lo", "up")
    for name in ("wlo1", "vpn0"):
        sh("ip", "link", "add", name, "type", "dummy")
        sh("ip", "link", "set", name, "up")
    sh("ip", "addr", "add", "192.168.1.173/24", "dev", "wlo1")
    sh("ip", "addr", "add", "10.8.0.4/24", "dev", "vpn0")
    # Full-tunnel VPN owns the default route, like a typical VPN client.
    sh("ip", "route", "add", "default", "dev", "vpn0", "metric", "50")
    sh("ip", "route", "add", "default", "via", "192.168.1.1", "dev", "wlo1", "metric", "600")
    # sing-box / clash style TUN clients steal all lookups with their own rule at prio 9000.
    sh("ip", "route", "add", "default", "dev", "vpn0", "table", "2022")
    sh("ip", "rule", "add", "priority", "9000", "lookup", "2022")
    sh("ip", "-6", "addr", "add", "2001:db8:1::173/64", "dev", "wlo1", "nodad")
    sh("ip", "-6", "route", "add", "default", "dev", "vpn0", "metric", "50")


def main() -> None:
    setup_topology()
    routing = Pyroute2RoutingAdapter()
    firewall = NftablesFirewallAdapter()
    journal = JsonPlanJournalAdapter(Path(tempfile.mkdtemp()) / "journal.json")
    service = ReconciliationService(routing, firewall, journal=journal)
    compiler = PlanCompiler()
    connections = [wifi(ipv6=True), vpn()]

    assert "dev vpn0" in route_get("198.51.100.10"), "precondition: VPN is the default"

    rules = [
        rule("Bank", "198.51.100.0/24"),
        rule("Intranet", "10.20.0.0/16", action=ActionType.USE_SELECTED_VPN, target=VPN_UUID),
        rule("Ads", "203.0.113.0/24", action=ActionType.BLOCK),
        rule("Bank v6", "2001:db8:beef::/48"),
    ]
    plan = compiler.compile(rules, connections)
    service.apply_plan(plan)
    service.apply_plan(compiler.compile(rules, connections))  # idempotent re-apply

    bypass = route_get("198.51.100.10")
    assert "via 192.168.1.1 dev wlo1" in bypass and "src 192.168.1.173" in bypass, bypass
    assert "dev vpn0" in route_get("10.20.1.1")
    bypass6 = route_get("2001:db8:beef::1")
    assert "via fe80::1 dev wlo1" in bypass6, bypass6
    assert "dev vpn0" in route_get("2001:db8:cafe::1")
    assert "dev vpn0" in route_get("9.9.9.9"), "unrelated traffic must stay on the VPN"
    rules_out = sh("ip", "rule", "show")
    assert rules_out.count(f"lookup {RoutingLayout.OVERRIDE_TABLE}") == 1, rules_out
    assert rules_out.count(f"lookup {RoutingLayout.GUARD_TABLE}") == 1, rules_out
    nft = sh("nft", "list", "table", "inet", "routepilot")
    assert "203.0.113.0/24" in nft and nft.count("reject") == 2, nft

    # Fail-closed: when the direct link disappears, the guard refuses instead of leaking.
    sh("ip", "link", "set", "wlo1", "down")
    refused = route_get("198.51.100.10").lower()
    assert "unreachable" in refused or "no route to host" in refused, refused
    sh("ip", "link", "set", "wlo1", "up")
    sh("ip", "route", "add", "default", "via", "192.168.1.1", "dev", "wlo1", "metric", "600")
    service.apply_plan(compiler.compile(rules, connections))
    assert "dev wlo1" in route_get("198.51.100.10")

    # Removing rules converges: no stale routes, rules or nft table remain.
    service.apply_plan(compiler.compile([], connections))
    assert "dev vpn0" in route_get("198.51.100.10")
    assert str(RoutingLayout.OVERRIDE_TABLE) not in sh("ip", "rule", "show")
    assert not firewall.is_table_present()

    service.apply_plan(compiler.compile(rules, connections))
    service.emergency_reset()
    assert str(RoutingLayout.OVERRIDE_TABLE) not in sh("ip", "rule", "show")
    assert sh("ip", "route", "show", "table", str(RoutingLayout.GUARD_TABLE)).strip() == ""
    assert not firewall.is_table_present()
    assert journal.load() is None

    print(json.dumps({"ok": True}))


if __name__ == "__main__":
    main()
