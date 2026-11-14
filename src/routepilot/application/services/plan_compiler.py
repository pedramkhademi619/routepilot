"""Compiler transforming domain rules into an atomic RoutePilotPlan."""

from datetime import UTC, datetime

from routepilot.application.services.routepilot_plan import RoutePilotPlan
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType


class PlanCompiler:
    """Compiles policy rules and active network state into an atomic kernel execution plan."""

    BASE_TABLE_ID = 10001
    BASE_RULE_PRIO = 10000
    MARK_MASK = 0x00FF0000

    def compile(
        self, rules: list[RoutingRule], active_connections: list[NetworkConnection]
    ) -> RoutePilotPlan:
        """Generates an atomic plan representing routing tables, ip rules, and nftables configuration."""
        {conn.uuid: conn for conn in active_connections}
        active_vpn_uuids: set[str] = {c.uuid for c in active_connections if c.is_vpn}

        direct_conn = next((c for c in active_connections if c.is_eligible_direct), None)

        tables_to_create: dict[int, RouteEntry] = {}
        rules_to_add: list[dict[str, int]] = []
        summary_lines: list[str] = []

        # Allocate table for direct physical egress if direct connection exists
        direct_table_id = self.BASE_TABLE_ID
        direct_mark = 0x10
        if direct_conn and direct_conn.ip4_config and direct_conn.ip4_config.gateway:
            tables_to_create[direct_table_id] = RouteEntry(
                destination="0.0.0.0/0",
                gateway=direct_conn.ip4_config.gateway,
                interface=direct_conn.interface,
                metric=10,
                table_id=direct_table_id,
            )
            rules_to_add.append(
                {
                    "table_id": direct_table_id,
                    "priority": self.BASE_RULE_PRIO + 10,
                    "fwmark": direct_mark,
                    "fwmask": self.MARK_MASK,
                    "family": 4,
                }
            )
            summary_lines.append(
                f"Configured direct routing table {direct_table_id} via {direct_conn.interface} "
                f"gw {direct_conn.ip4_config.gateway}"
            )

        # Build CIDR sets for nftables
        bypass_v4_elements: list[str] = []
        bypass_v6_elements: list[str] = []
        block_v4_elements: list[str] = []
        block_v6_elements: list[str] = []
        cgroup_matches: list[str] = []

        for rule in sorted(rules, key=lambda r: (r.priority, r.id)):
            if not rule.enabled:
                continue

            # Check activation condition
            if rule.condition.type == ConditionType.ANY_VPN_ACTIVE and not active_vpn_uuids:
                continue
            if rule.condition.type == ConditionType.SPECIFIC_VPN_ACTIVE:
                if (
                    not rule.condition.target_vpn_uuid
                    or rule.condition.target_vpn_uuid not in active_vpn_uuids
                ):
                    continue

            # Action evaluation
            if rule.action.type == ActionType.USE_DIRECT:
                if direct_conn:
                    if rule.selector.type in (SelectorType.IP_ADDRESS, SelectorType.CIDR):
                        val = rule.selector.value
                        if ":" in val:
                            bypass_v6_elements.append(val)
                        else:
                            bypass_v4_elements.append(val)
                    elif rule.selector.type == SelectorType.APPLICATION:
                        cgroup_matches.append(
                            f'socket cgroupv2 level 2 "user.slice/user-1000.slice/user@1000.service/app.slice/routepilot-app-{rule.selector.value}.scope" meta mark set {hex(direct_mark)}'
                        )
                    summary_lines.append(
                        f"Rule '{rule.name}': Direct bypass via {direct_conn.interface}"
                    )
                else:
                    # Direct connection missing
                    if rule.fallback.behavior == FailureBehavior.BLOCK:
                        if ":" in rule.selector.value:
                            block_v6_elements.append(rule.selector.value)
                        else:
                            block_v4_elements.append(rule.selector.value)
                        summary_lines.append(
                            f"Rule '{rule.name}': Target unavailable -> fail-closed (blocked)"
                        )

            elif rule.action.type == ActionType.BLOCK:
                if rule.selector.type in (SelectorType.IP_ADDRESS, SelectorType.CIDR):
                    val = rule.selector.value
                    if ":" in val:
                        block_v6_elements.append(val)
                    else:
                        block_v4_elements.append(val)
                summary_lines.append(f"Rule '{rule.name}': Explicitly blocked")

        # Synthesize nftables ruleset
        v4_elems_str = ", ".join(bypass_v4_elements) if bypass_v4_elements else ""
        block_v4_str = ", ".join(block_v4_elements) if block_v4_elements else ""

        nft_lines = [
            "table inet routepilot {",
            "    set bypass_v4 {",
            "        type ipv4_addr",
            "        flags interval",
        ]
        if bypass_v4_elements:
            nft_lines.append(f"        elements = {{ {v4_elems_str} }}")
        nft_lines.extend(
            [
                "    }",
                "    set block_v4 {",
                "        type ipv4_addr",
                "        flags interval",
            ]
        )
        if block_v4_elements:
            nft_lines.append(f"        elements = {{ {block_v4_str} }}")
        nft_lines.extend(
            [
                "    }",
                "    chain routepilot_output {",
                "        type route hook output priority mangle; policy accept;",
            ]
        )
        if block_v4_elements:
            nft_lines.append("        ip daddr @block_v4 drop")
        if bypass_v4_elements:
            nft_lines.append(f"        ip daddr @bypass_v4 meta mark set {hex(direct_mark)}")
        for cg in cgroup_matches:
            nft_lines.append(f"        {cg}")
        nft_lines.extend(
            [
                "    }",
                "}",
            ]
        )
        nft_ruleset = "\n".join(nft_lines) + "\n"

        rollback_tables = list(tables_to_create.keys())
        rollback_rule_prios = [r["priority"] for r in rules_to_add]

        return RoutePilotPlan(
            created_at=datetime.now(UTC).isoformat(),
            tables_to_create=tables_to_create,
            rules_to_add=rules_to_add,
            nft_ruleset_content=nft_ruleset,
            summary_lines=summary_lines,
            rollback_tables=rollback_tables,
            rollback_rule_priorities=rollback_rule_prios,
        )
