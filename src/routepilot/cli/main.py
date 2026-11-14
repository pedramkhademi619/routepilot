"""RoutePilot Command Line Interface."""

import argparse
import asyncio
import sys

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.policy_evaluator import PolicyEvaluator
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.infrastructure.adapters.json_policy_repository_adapter import JsonPolicyRepositoryAdapter
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.infrastructure.adapters.nftables_firewall_adapter import NftablesFirewallAdapter
from routepilot.infrastructure.adapters.nm_discovery_adapter import NetworkManagerDiscoveryAdapter
from routepilot.infrastructure.adapters.pyroute2_routing_adapter import Pyroute2RoutingAdapter


class RoutePilotCli:
    """Command-line interface for RoutePilot inspection, evaluation, and management."""

    def __init__(self) -> None:
        self.policy_repo = JsonPolicyRepositoryAdapter()
        self.routing_adapter = Pyroute2RoutingAdapter()
        self.firewall_adapter = NftablesFirewallAdapter()
        self.reconciliation = ReconciliationService(self.routing_adapter, self.firewall_adapter)

    def run(self, argv: list[str]) -> int:
        parser = argparse.ArgumentParser(
            prog="routepilot",
            description="RoutePilot: Selective VPN bypass and traffic policy routing utility"
        )
        parser.add_argument("--mock", action="store_true", help="Use mock network adapters for offline testing")
        subparsers = parser.add_subparsers(dest="command", required=True)

        # status command
        subparsers.add_parser("status", help="Display active network connections and VPN state")

        # rules command
        subparsers.add_parser("rules", help="List configured traffic routing rules")

        # eval command
        eval_parser = subparsers.add_parser("eval", help="Evaluate routing decision for a destination")
        eval_parser.add_argument("target", help="Destination IP or domain name")

        # reset command
        subparsers.add_parser("reset", help="Emergency reset of RoutePilot tables and rules")

        args = parser.parse_args(argv)

        discovery_adapter = MockDiscoveryAdapter() if args.mock else NetworkManagerDiscoveryAdapter()
        discovery_service = DiscoveryService(discovery_adapter)

        if args.command == "status":
            return self._cmd_status(discovery_service)
        elif args.command == "rules":
            return self._cmd_rules()
        elif args.command == "eval":
            return self._cmd_eval(discovery_service, args.target)
        elif args.command == "reset":
            return self._cmd_reset()

        return 0

    def _cmd_status(self, discovery_service: DiscoveryService) -> int:
        conns = asyncio.run(discovery_service.refresh())
        print(f"\nDiscovered {len(conns)} network connection(s):")
        print("=" * 60)
        for c in conns:
            vpn_tag = "[VPN]" if c.is_vpn else "[DIRECT]" if c.is_eligible_direct else "[OTHER]"
            default_tag = " (Default Gateway)" if c.is_default else ""
            print(f" {vpn_tag:<8} {c.id:<25} iface: {c.interface:<8} metric: {c.metric}{default_tag}")
            if c.ip4_config and c.ip4_config.addresses:
                print(f"          IPs: {', '.join(c.ip4_config.addresses)} | Gateway: {c.ip4_config.gateway}")
        print("=" * 60)
        return 0

    def _cmd_rules(self) -> int:
        doc = self.policy_repo.load_policy()
        rules = doc.sort_by_priority()
        print(f"\nConfigured Traffic Rules ({len(rules)} total):")
        print("=" * 70)
        for r in rules:
            status = "ON " if r.enabled else "OFF"
            print(f" [{status}] Prio {r.priority:<4} | {r.name:<25} | {r.selector.type.value}:{r.selector.value}")
            print(f"       -> Action: {r.action.type.value} | Condition: {r.condition.type.value}")
        print("=" * 70)
        return 0

    def _cmd_eval(self, discovery_service: DiscoveryService, target: str) -> int:
        conns = asyncio.run(discovery_service.refresh())
        doc = self.policy_repo.load_policy()
        evaluator = PolicyEvaluator(doc.rules)
        res = evaluator.evaluate(target, conns)

        print(f"\nPolicy Evaluation for: {target}")
        print("=" * 60)
        print(f" Effective Action : {res.action.value.upper()}")
        print(f" Blocked (Dropped): {res.is_blocked}")
        if res.target_connection:
            print(f" Egress Interface : {res.target_connection.interface} ({res.target_connection.id})")
        print(f" Explanation      : {res.explanation}")
        if res.conflicts:
            print(f" Warnings         : {'; '.join(res.conflicts)}")
        print("=" * 60)
        return 0

    def _cmd_reset(self) -> int:
        print("Purging RoutePilot tables and rules...")
        self.reconciliation.emergency_reset()
        print("Reset complete.")
        return 0


def main() -> None:
    cli = RoutePilotCli()
    sys.exit(cli.run(sys.argv[1:]))


if __name__ == "__main__":
    main()
