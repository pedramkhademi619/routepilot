"""RoutePilot Command Line Interface."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from routepilot import __version__
from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.policy_apply_service import PolicyApplyService
from routepilot.application.services.policy_evaluator import PolicyEvaluator
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.cli.elevation import is_root, run_elevated
from routepilot.domain.models.routepilot_plan import RoutePilotPlan
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort
from routepilot.infrastructure.adapters.json_plan_journal_adapter import JsonPlanJournalAdapter
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.infrastructure.adapters.nftables_firewall_adapter import NftablesFirewallAdapter
from routepilot.infrastructure.adapters.nm_discovery_adapter import NetworkManagerDiscoveryAdapter
from routepilot.infrastructure.adapters.pyroute2_routing_adapter import Pyroute2RoutingAdapter
from routepilot.infrastructure.adapters.systemd_resolved_adapter import SystemdResolvedAdapter
from routepilot.infrastructure.legacy_state import remove_legacy_host_routes

PRIVILEGED_COMMANDS = ("apply", "reset")


class RoutePilotCli:
    """Command-line interface for RoutePilot inspection, evaluation, and management."""

    def run(self, argv: list[str]) -> int:
        args = self._parser().parse_args(argv)
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("routepilot").setLevel(logging.DEBUG if args.verbose else logging.WARNING)
        self.policy_repo = JsonPolicyRepositoryAdapter(file_path=args.policy)

        if args.command in PRIVILEGED_COMMANDS:
            if args.mock:
                print("Error: --mock cannot be combined with commands that change the kernel.")
                return 2
            if not is_root():
                return run_elevated(self._elevated_args(args))

        handlers = {
            "status": self._cmd_status,
            "rules": self._cmd_rules,
            "eval": self._cmd_eval,
            "plan": self._cmd_plan,
            "apply": self._cmd_apply,
            "reset": self._cmd_reset,
        }
        return handlers[args.command](args)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="routepilot",
            description="RoutePilot: selective VPN bypass and traffic policy routing for Linux",
        )
        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        parser.add_argument(
            "--mock", action="store_true", help="Use mock network adapters for offline testing"
        )
        parser.add_argument(
            "--policy", help="Policy file (default: ~/.config/routepilot/policy.json)"
        )
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
        sub = parser.add_subparsers(dest="command", required=True)
        sub.add_parser("status", help="Show network connections and VPN state")
        sub.add_parser("rules", help="List configured traffic routing rules")
        eval_parser = sub.add_parser("eval", help="Explain the routing decision for a destination")
        eval_parser.add_argument("target", help="Destination IP or domain name")
        sub.add_parser("plan", help="Show the kernel changes 'apply' would make (dry run)")
        sub.add_parser("apply", help="Apply the policy to the kernel (asks for authorization)")
        sub.add_parser("reset", help="Remove all RoutePilot routes, rules and nftables state")
        return parser

    def _elevated_args(self, args: argparse.Namespace) -> list[str]:
        # Root cannot see the user's environment, so pass the policy location explicitly.
        elevated = ["--policy", str(Path(self.policy_repo.file_path).resolve())]
        if args.verbose:
            elevated.append("--verbose")
        return [*elevated, args.command]

    def _discovery(self, args: argparse.Namespace) -> NetworkDiscoveryPort:
        return MockDiscoveryAdapter() if args.mock else NetworkManagerDiscoveryAdapter()

    def _reconciliation(self) -> ReconciliationService:
        return ReconciliationService(
            Pyroute2RoutingAdapter(),
            NftablesFirewallAdapter(),
            dns_port=SystemdResolvedAdapter(),
            journal=JsonPlanJournalAdapter(),
        )

    def _apply_service(self, args: argparse.Namespace) -> PolicyApplyService:
        return PolicyApplyService(
            self._discovery(args), SystemdResolvedAdapter(), self._reconciliation()
        )

    def _cmd_status(self, args: argparse.Namespace) -> int:
        conns = asyncio.run(DiscoveryService(self._discovery(args)).refresh())
        print(f"\nDiscovered {len(conns)} network connection(s):")
        print("=" * 60)
        for c in conns:
            tag = "[VPN]" if c.is_vpn else "[DIRECT]" if c.is_eligible_direct else "[OTHER]"
            default_tag = " (Default Gateway)" if c.is_default else ""
            print(f" {tag:<8} {c.id:<25} iface: {c.interface:<8} metric: {c.metric}{default_tag}")
            if c.ip4_config and c.ip4_config.addresses:
                print(
                    f"          IPs: {', '.join(c.ip4_config.addresses)} | "
                    f"Gateway: {c.ip4_config.gateway}"
                )
        print("=" * 60)
        return 0

    def _cmd_rules(self, args: argparse.Namespace) -> int:
        rules = self.policy_repo.load_policy().sort_by_priority()
        print(f"\nConfigured Traffic Rules ({len(rules)} total):")
        print("=" * 70)
        for r in rules:
            status = "ON " if r.enabled else "OFF"
            print(
                f" [{status}] Prio {r.priority:<4} | {r.name:<25} | "
                f"{r.selector.type.value}:{r.selector.value}"
            )
            print(f"       -> Action: {r.action.type.value} | Condition: {r.condition.type.value}")
        print("=" * 70)
        return 0

    def _cmd_eval(self, args: argparse.Namespace) -> int:
        conns = asyncio.run(DiscoveryService(self._discovery(args)).refresh())
        res = PolicyEvaluator(self.policy_repo.load_policy().rules).evaluate(args.target, conns)

        print(f"\nPolicy Evaluation for: {args.target}")
        print("=" * 60)
        print(f" Effective Action : {res.action.value.upper()}")
        print(f" Blocked (Dropped): {res.is_blocked}")
        if res.target_connection:
            print(
                f" Egress Interface : {res.target_connection.interface} "
                f"({res.target_connection.id})"
            )
        print(f" Explanation      : {res.explanation}")
        if res.conflicts:
            print(f" Warnings         : {'; '.join(res.conflicts)}")
        print("=" * 60)
        return 0

    def _cmd_plan(self, args: argparse.Namespace) -> int:
        rules = self.policy_repo.load_policy().rules
        service = PolicyApplyService(
            self._discovery(args),
            SystemdResolvedAdapter(),
            ReconciliationService(Pyroute2RoutingAdapter(), NftablesFirewallAdapter()),
        )
        self._print_plan(asyncio.run(service.build_plan(rules)), verbose=True)
        return 0

    def _cmd_apply(self, args: argparse.Namespace) -> int:
        print("=== RoutePilot: applying traffic routing policy ===")
        rules = self.policy_repo.load_policy().rules
        service = self._apply_service(args)
        remove_legacy_host_routes(Pyroute2RoutingAdapter())
        try:
            plan = asyncio.run(service.apply(rules))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        self._print_plan(plan, verbose=False)
        print("\nRoutePilot policy applied.")
        return 0

    def _cmd_reset(self, args: argparse.Namespace) -> int:
        print("Removing RoutePilot routes, ip rules, nftables table and split DNS...")
        remove_legacy_host_routes(Pyroute2RoutingAdapter())
        try:
            self._reconciliation().emergency_reset()
        except Exception as e:
            print(f"Error during reset: {e}", file=sys.stderr)
            return 1
        print("Reset complete.")
        return 0

    @staticmethod
    def _print_plan(plan: RoutePilotPlan, verbose: bool) -> None:
        for line in plan.summary_lines or ["No enabled rules apply right now."]:
            print(f" • {line}")
        for warning in plan.warnings:
            print(f" ! {warning}")
        if not verbose:
            return
        print("\nRoutes:")
        for r in plan.routes:
            via = f" via {r.gateway}" if r.gateway else ""
            dev = f" dev {r.interface}" if r.interface else ""
            print(f"  table {r.table_id}: {r.route_type.value} {r.destination}{via}{dev}")
        print("ip rules:")
        for rule in plan.rules:
            print(f"  prio {rule.priority} lookup {rule.table_id} (IPv{rule.family})")
        if plan.split_dns:
            print("Split DNS:")
            for iface, domains in plan.split_dns.items():
                print(f"  {iface}: {' '.join('~' + d for d in domains)}")
        if plan.nft_ruleset:
            print("nftables:\n" + plan.nft_ruleset)


def main() -> None:
    sys.exit(RoutePilotCli().run(sys.argv[1:]))


if __name__ == "__main__":
    main()
