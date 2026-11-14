"""Service for deterministic policy evaluation and conflict detection."""

import ipaddress

from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType


class PolicyEvaluator:
    """Evaluates routing rules against live network state with deterministic priority."""

    def __init__(self, rules: list[RoutingRule]) -> None:
        self.rules = sorted(rules, key=lambda r: (r.priority, r.id))

    def evaluate(
        self,
        target: str,
        active_connections: list[NetworkConnection],
        app_id: str | None = None,
    ) -> PolicyEvaluationResult:
        """Evaluates effective policy for a given destination IP, domain, or application ID."""
        active_conn_map = {conn.uuid: conn for conn in active_connections}
        active_vpn_uuids: set[str] = {conn.uuid for conn in active_connections if conn.is_vpn}

        matching_rules: list[RoutingRule] = []
        conflicts: list[str] = []

        # 1. Filter enabled rules that match activation condition and selector
        for rule in self.rules:
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

            # Check selector match
            if self._matches_selector(rule, target, app_id):
                matching_rules.append(rule)

        if not matching_rules:
            return PolicyEvaluationResult(
                action=ActionType.FOLLOW_SYSTEM,
                explanation="No explicit RoutePilot rules matched. Following default system routing table.",
            )

        # 2. Check for priority conflicts among top matching rules
        top_rule = matching_rules[0]
        same_priority_rules = [
            r for r in matching_rules if r.priority == top_rule.priority and r.id != top_rule.id
        ]
        for conflict_rule in same_priority_rules:
            if conflict_rule.action.type != top_rule.action.type:
                conflicts.append(
                    f"Warning: Rule '{top_rule.name}' and '{conflict_rule.name}' have identical "
                    f"priority ({top_rule.priority}) with conflicting actions. "
                    f"Tie broken deterministically by rule ID."
                )

        # 3. Resolve target egress connection and failure policies
        explanation_parts = [f"Matched rule '{top_rule.name}' (Priority {top_rule.priority})."]

        if len(matching_rules) > 1:
            lower_rule = matching_rules[1]
            explanation_parts.append(
                f"Overrode lower-priority rule '{lower_rule.name}' (Priority {lower_rule.priority})."
            )

        if top_rule.action.type == ActionType.BLOCK:
            return PolicyEvaluationResult(
                matched_rule=top_rule,
                action=ActionType.BLOCK,
                is_blocked=True,
                explanation=" ".join(explanation_parts) + " Traffic is explicitly blocked.",
                conflicts=conflicts,
            )

        if top_rule.action.type == ActionType.USE_DIRECT:
            direct_conn = next((c for c in active_connections if c.is_eligible_direct), None)
            if top_rule.action.target_connection_uuid:
                pinned = active_conn_map.get(top_rule.action.target_connection_uuid)
                if pinned and pinned.is_eligible_direct:
                    direct_conn = pinned

            if direct_conn:
                explanation_parts.append(
                    f"Routing directly via physical connection '{direct_conn.id}' ({direct_conn.interface}), "
                    f"bypassing active VPN."
                )
                return PolicyEvaluationResult(
                    matched_rule=top_rule,
                    action=ActionType.USE_DIRECT,
                    target_connection=direct_conn,
                    explanation=" ".join(explanation_parts),
                    conflicts=conflicts,
                )
            else:
                return self._handle_unavailable_target(
                    top_rule, "direct physical internet egress", conflicts
                )

        if top_rule.action.type == ActionType.USE_SELECTED_VPN:
            target_uuid = top_rule.action.target_connection_uuid
            target_vpn = active_conn_map.get(target_uuid) if target_uuid else None

            if target_vpn and target_vpn.is_vpn:
                explanation_parts.append(
                    f"Exclusively routing via VPN '{target_vpn.id}' ({target_vpn.interface})."
                )
                return PolicyEvaluationResult(
                    matched_rule=top_rule,
                    action=ActionType.USE_SELECTED_VPN,
                    target_connection=target_vpn,
                    explanation=" ".join(explanation_parts),
                    conflicts=conflicts,
                )
            else:
                return self._handle_unavailable_target(
                    top_rule,
                    f"required VPN (UUID {target_uuid or 'unspecified'})",
                    conflicts,
                )

        if top_rule.action.type == ActionType.EXCLUDE_VPN:
            excluded_set = set(top_rule.action.excluded_vpn_uuids)
            eligible_non_excluded = [
                c
                for c in active_connections
                if c.uuid not in excluded_set and (c.is_eligible_direct or c.is_vpn)
            ]
            if eligible_non_excluded:
                chosen = eligible_non_excluded[0]
                explanation_parts.append(
                    f"Excluded specified VPNs. Routing through eligible connection '{chosen.id}' ({chosen.interface})."
                )
                return PolicyEvaluationResult(
                    matched_rule=top_rule,
                    action=ActionType.EXCLUDE_VPN,
                    target_connection=chosen,
                    explanation=" ".join(explanation_parts),
                    conflicts=conflicts,
                )
            else:
                return self._handle_unavailable_target(
                    top_rule, "eligible non-excluded connection", conflicts
                )

        return PolicyEvaluationResult(
            matched_rule=top_rule,
            action=ActionType.FOLLOW_SYSTEM,
            explanation=" ".join(explanation_parts) + " Following default system routing table.",
            conflicts=conflicts,
        )

    def _matches_selector(self, rule: RoutingRule, target: str, app_id: str | None) -> bool:
        sel = rule.selector
        if sel.type == SelectorType.APPLICATION:
            return app_id is not None and (sel.value == app_id or sel.value in app_id)

        if sel.type in (SelectorType.IP_ADDRESS, SelectorType.CIDR):
            try:
                target_ip = ipaddress.ip_address(target)
                rule_net = ipaddress.ip_network(sel.value, strict=False)
                return target_ip in rule_net
            except ValueError:
                return False

        if sel.type == SelectorType.DOMAIN:
            return target.lower() == sel.value.lower()

        if sel.type == SelectorType.DOMAIN_AND_SUBDOMAINS:
            root = sel.value.lower().lstrip("*.")
            t_lower = target.lower()
            return t_lower == root or t_lower.endswith("." + root)

        return False

    def _handle_unavailable_target(
        self, rule: RoutingRule, target_description: str, conflicts: list[str]
    ) -> PolicyEvaluationResult:
        if rule.fallback.behavior == FailureBehavior.BLOCK:
            return PolicyEvaluationResult(
                matched_rule=rule,
                action=ActionType.BLOCK,
                is_blocked=True,
                explanation=(
                    f"Traffic blocked by fail-closed policy under rule '{rule.name}'. "
                    f"Target {target_description} is currently disconnected/unavailable."
                ),
                conflicts=conflicts,
            )
        else:
            return PolicyEvaluationResult(
                matched_rule=rule,
                action=ActionType.FOLLOW_SYSTEM,
                is_blocked=False,
                explanation=(
                    f"Target {target_description} under rule '{rule.name}' is unavailable. "
                    f"Falling back to system default routing per user consent."
                ),
                conflicts=conflicts,
            )
