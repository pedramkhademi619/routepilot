"""Compiler transforming domain rules into a declarative RoutePilotPlan."""

import ipaddress
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from routepilot.application.services.egress_resolver import EgressResolver
from routepilot.application.services.routing_layout import RoutingLayout
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.models.route_type import RouteType
from routepilot.domain.models.routepilot_plan import RoutePilotPlan
from routepilot.domain.models.rpdb_rule import RpdbRule
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class PlanCompiler:
    """Compiles policy rules and live network state into the kernel state RoutePilot owns.

    Compilation is pure: domain names must be resolved beforehand (see
    :meth:`resolution_requests`) and passed in, which keeps the compiler deterministic and
    unit-testable without network access.
    """

    def __init__(self, egress: EgressResolver | None = None) -> None:
        self._egress = egress or EgressResolver()

    def resolution_requests(
        self, rules: list[RoutingRule], connections: list[NetworkConnection]
    ) -> dict[str, str | None]:
        """Returns hostnames to resolve, mapped to the interface whose DNS should answer.

        Resolving through the target link's own DNS servers returns the addresses that
        clients on that path will actually connect to (important for geo-DNS and CDNs).
        """
        requests: dict[str, str | None] = {}
        for rule in self._enforceable(rules, connections):
            if not rule.selector.is_domain:
                continue
            target = self._egress.resolve(rule, connections)
            interface = target.interface if target else None
            for hostname in rule.selector.hostnames():
                requests.setdefault(hostname, interface)
        return requests

    def compile(
        self,
        rules: list[RoutingRule],
        connections: list[NetworkConnection],
        resolved: Mapping[str, Sequence[str]] | None = None,
    ) -> RoutePilotPlan:
        """Generates the routes, ip rules, nftables table and split DNS for ``rules``."""
        resolved = resolved or {}
        routes: list[RouteEntry] = []
        blocked: list[IPNetwork] = []
        split_dns: dict[str, list[str]] = {}
        summary: list[str] = []
        warnings: list[str] = []
        claimed: set[IPNetwork] = set()

        for rule in self._enforceable(rules, connections):
            if rule.selector.type == SelectorType.APPLICATION:
                warnings.append(
                    f"Rule '{rule.name}': per-application routing is not enforced yet; skipped."
                )
                continue

            networks = self._networks_for(rule, resolved)
            if not networks:
                warnings.append(f"Rule '{rule.name}': could not resolve '{rule.selector.value}'.")
                continue

            fresh = [n for n in networks if n not in claimed]
            if len(fresh) < len(networks):
                warnings.append(
                    f"Rule '{rule.name}': {len(networks) - len(fresh)} destination(s) already "
                    f"claimed by a higher-priority rule (shared CDN address?)."
                )
            claimed.update(fresh)
            if not fresh:
                continue

            action = rule.action.type
            if action == ActionType.BLOCK:
                blocked.extend(fresh)
                summary.append(f"Rule '{rule.name}': blocking {len(fresh)} destination(s)")
                continue

            if action == ActionType.FOLLOW_SYSTEM:
                for table in RoutingLayout.owned_tables():
                    routes.extend(self._route(n, table, RouteType.THROW) for n in fresh)
                summary.append(f"Rule '{rule.name}': following system routing")
                continue

            target = self._egress.resolve(rule, connections)
            if target is not None:
                pinned = self._pin(rule, fresh, target, routes, warnings)
                summary.append(
                    f"Rule '{rule.name}': {pinned} destination(s) via {target.interface} "
                    f"({target.id})"
                )
                if rule.selector.is_domain:
                    links = split_dns.setdefault(target.interface, [])
                    if rule.selector.root_domain not in links:
                        links.append(rule.selector.root_domain)
            else:
                summary.append(f"Rule '{rule.name}': target unavailable")

            if rule.fallback.behavior == FailureBehavior.BLOCK:
                routes.extend(
                    self._route(n, RoutingLayout.GUARD_TABLE, RouteType.UNREACHABLE) for n in fresh
                )
                if target is None:
                    summary.append(f"Rule '{rule.name}': fail-closed, traffic refused")

        return RoutePilotPlan(
            created_at=datetime.now(UTC).isoformat(),
            routes=routes,
            rules=self._rules_for(routes),
            nft_ruleset=self._nft_ruleset(blocked),
            split_dns=split_dns,
            summary_lines=summary,
            warnings=warnings,
        )

    def _enforceable(
        self, rules: list[RoutingRule], connections: list[NetworkConnection]
    ) -> list[RoutingRule]:
        """Enabled rules whose activation condition holds, in deterministic priority order."""
        return [
            rule
            for rule in sorted(rules, key=lambda r: (r.priority, r.id))
            if rule.enabled and rule.condition.is_satisfied(connections)
        ]

    def _networks_for(
        self, rule: RoutingRule, resolved: Mapping[str, Sequence[str]]
    ) -> list[IPNetwork]:
        values = (
            [rule.selector.value]
            if rule.selector.is_network
            else [ip for host in rule.selector.hostnames() for ip in resolved.get(host, [])]
        )
        networks: list[IPNetwork] = []
        for value in values:
            try:
                network = ipaddress.ip_network(value, strict=False)
            except ValueError:
                continue
            if network not in networks:
                networks.append(network)
        return networks

    def _pin(
        self,
        rule: RoutingRule,
        networks: list[IPNetwork],
        target: NetworkConnection,
        routes: list[RouteEntry],
        warnings: list[str],
    ) -> int:
        """Adds override routes towards ``target``; returns how many could be pinned."""
        pinned = 0
        endpoints = self._vpn_endpoints([target]) if target.is_vpn else []
        for network in networks:
            if any(endpoint in network for endpoint in endpoints):
                warnings.append(
                    f"Rule '{rule.name}': {network} contains the VPN server {target.interface} "
                    f"connects to; routing it into the tunnel would loop. Skipped."
                )
                continue
            # Tunnels are point-to-point: route by device. Physical links need their gateway.
            gateway = None if target.is_vpn else target.gateway_for(network.version)
            if not target.is_vpn and gateway is None:
                warnings.append(
                    f"Rule '{rule.name}': {target.interface} has no IPv{network.version} "
                    f"gateway; {network} left to the system."
                )
                continue
            routes.append(
                RouteEntry(
                    destination=str(network),
                    gateway=gateway,
                    interface=target.interface,
                    table_id=RoutingLayout.OVERRIDE_TABLE,
                )
            )
            pinned += 1
        return pinned

    @staticmethod
    def _vpn_endpoints(
        connections: list[NetworkConnection],
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        endpoints = []
        for conn in connections:
            try:
                if conn.server_endpoint:
                    endpoints.append(ipaddress.ip_address(conn.server_endpoint))
            except ValueError:
                continue
        return endpoints

    @staticmethod
    def _route(network: IPNetwork, table_id: int, route_type: RouteType) -> RouteEntry:
        return RouteEntry(destination=str(network), table_id=table_id, route_type=route_type)

    @staticmethod
    def _rules_for(routes: list[RouteEntry]) -> list[RpdbRule]:
        """One ip rule per (table, family) that actually has routes."""
        used = sorted({(r.table_id, r.family) for r in routes})
        return [
            RpdbRule(
                priority=RoutingLayout.priority_for_table(table_id),
                table_id=table_id,
                family=family,
            )
            for table_id, family in used
        ]

    @staticmethod
    def _nft_ruleset(blocked: list[IPNetwork]) -> str | None:
        """Builds table inet routepilot rejecting explicitly blocked destinations."""
        if not blocked:
            return None
        v4 = ", ".join(str(n) for n in blocked if n.version == 4)
        v6 = ", ".join(str(n) for n in blocked if n.version == 6)
        lines = ["table inet routepilot {"]
        for name, addr_type, elements in (
            ("block_v4", "ipv4_addr", v4),
            ("block_v6", "ipv6_addr", v6),
        ):
            lines += [f"    set {name} {{", f"        type {addr_type}", "        flags interval"]
            lines += ["        auto-merge"]
            if elements:
                lines.append(f"        elements = {{ {elements} }}")
            lines.append("    }")
        lines += [
            "    chain output {",
            "        type filter hook output priority filter; policy accept;",
            "        ip daddr @block_v4 reject",
            "        ip6 daddr @block_v6 reject",
            "    }",
            "}",
        ]
        return "\n".join(lines) + "\n"
