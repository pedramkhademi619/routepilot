"""Service for deterministic policy evaluation and conflict detection."""

import ipaddress

from routepilot.application.services.egress_resolver import EgressResolver
from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType


class PolicyEvaluator:
    """Evaluates routing rules against live network state with deterministic priority."""

    def __init__(self, rules: list[RoutingRule], egress: EgressResolver | None = None) -> None:
        self.rules = sorted(rules, key=lambda r: (r.priority, r.id))
        self._egress = egress or EgressResolver()

    def evaluate(
        self,
        target: str,
        active_connections: list[NetworkConnection],
        app_id: str | None = None,
    ) -> PolicyEvaluationResult:
        """Evaluates effective policy for a given destination IP, domain, or application ID."""
        matching_rules = [
            rule
            for rule in self.rules
            if rule.enabled
            and rule.condition.is_satisfied(active_connections)
            and self._matches_selector(rule, target, app_id)
        ]

        if not matching_rules:
            return PolicyEvaluationResult(
                action=ActionType.FOLLOW_SYSTEM,
                explanation="No explicit RoutePilot rules matched. Following default system routing table.",
            )

        top_rule = matching_rules[0]
        conflicts = [
            f"Warning: Rule '{top_rule.name}' and '{other.name}' have identical "
            f"priority ({top_rule.priority}) with conflicting actions. "
            f"Tie broken deterministically by rule ID."
            for other in matching_rules[1:]
            if other.priority == top_rule.priority and other.action.type != top_rule.action.type
        ]

        explanation_parts = [f"Matched rule '{top_rule.name}' (Priority {top_rule.priority})."]
        if len(matching_rules) > 1:
            lower_rule = matching_rules[1]
            explanation_parts.append(
                f"Overrode lower-priority rule '{lower_rule.name}' (Priority {lower_rule.priority})."
            )

        action = top_rule.action.type
        if action == ActionType.BLOCK:
            return PolicyEvaluationResult(
                matched_rule=top_rule,
                action=ActionType.BLOCK,
                is_blocked=True,
                explanation=" ".join(explanation_parts) + " Traffic is explicitly blocked.",
                conflicts=conflicts,
            )

        if action == ActionType.FOLLOW_SYSTEM:
            return PolicyEvaluationResult(
                matched_rule=top_rule,
                action=ActionType.FOLLOW_SYSTEM,
                explanation=" ".join(explanation_parts)
                + " Following default system routing table.",
                conflicts=conflicts,
            )

        egress = self._egress.resolve(top_rule, active_connections)
        if egress is None:
            return self._handle_unavailable_target(
                top_rule, self._describe_target(top_rule), conflicts
            )

        if action == ActionType.USE_DIRECT and not egress.is_vpn:
            explanation_parts.append(
                f"Routing directly via physical connection '{egress.id}' ({egress.interface}), "
                f"bypassing active VPN."
            )
        elif action == ActionType.EXCLUDE_VPN:
            explanation_parts.append(
                f"Excluded specified VPNs. Routing through eligible connection "
                f"'{egress.id}' ({egress.interface})."
            )
        else:
            explanation_parts.append(f"Exclusively routing via '{egress.id}' ({egress.interface}).")

        return PolicyEvaluationResult(
            matched_rule=top_rule,
            action=action,
            target_connection=egress,
            explanation=" ".join(explanation_parts),
            conflicts=conflicts,
        )

    def _matches_selector(self, rule: RoutingRule, target: str, app_id: str | None) -> bool:
        sel = rule.selector
        if sel.type == SelectorType.APPLICATION:
            return app_id is not None and (sel.value == app_id or sel.value in app_id)

        if sel.is_network:
            try:
                return ipaddress.ip_address(target) in ipaddress.ip_network(sel.value, strict=False)
            except ValueError:
                return False

        t_lower = target.lower().rstrip(".")
        if sel.type == SelectorType.DOMAIN:
            return t_lower == sel.root_domain

        if sel.type == SelectorType.DOMAIN_AND_SUBDOMAINS:
            root = sel.root_domain
            return t_lower == root or t_lower.endswith("." + root)

        return False

    def _describe_target(self, rule: RoutingRule) -> str:
        if rule.action.type == ActionType.USE_DIRECT:
            return "direct physical internet egress"
        if rule.action.type == ActionType.USE_SELECTED_VPN:
            return f"required VPN (UUID {rule.action.target_connection_uuid or 'any active VPN'})"
        return "eligible non-excluded connection"

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
