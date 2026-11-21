"""Chooses the live connection a rule's action should send traffic through."""

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule


class EgressResolver:
    """Maps a routing rule onto a concrete egress connection (or None when unavailable)."""

    def resolve(
        self, rule: RoutingRule, connections: list[NetworkConnection]
    ) -> NetworkConnection | None:
        target = self._primary_target(rule, connections)
        if target is None and rule.fallback.behavior == FailureBehavior.USE_ALTERNATIVE:
            alt_uuid = rule.fallback.alternative_connection_uuid
            target = next((c for c in connections if c.uuid == alt_uuid and c.is_active), None)
        return target

    def direct_connection(
        self, connections: list[NetworkConnection], pinned_uuid: str | None = None
    ) -> NetworkConnection | None:
        """Returns the pinned physical connection, else the one with the best metric."""
        eligible = [c for c in connections if c.is_eligible_direct]
        pinned = next((c for c in eligible if c.uuid == pinned_uuid), None)
        if pinned:
            return pinned
        return min(eligible, key=lambda c: c.metric, default=None)

    def _primary_target(
        self, rule: RoutingRule, connections: list[NetworkConnection]
    ) -> NetworkConnection | None:
        action = rule.action
        active_vpns = [c for c in connections if c.is_vpn and c.is_active]

        if action.type == ActionType.USE_DIRECT:
            return self.direct_connection(connections, action.target_connection_uuid)

        if action.type == ActionType.USE_SELECTED_VPN:
            if action.target_connection_uuid:
                return next(
                    (c for c in active_vpns if c.uuid == action.target_connection_uuid), None
                )
            # No VPN pinned: any active VPN, preferring the one that owns the default route.
            return min(active_vpns, key=lambda c: (not c.is_default, c.metric), default=None)

        if action.type == ActionType.EXCLUDE_VPN:
            excluded = set(action.excluded_vpn_uuids)
            return next(
                (
                    c
                    for c in connections
                    if c.uuid not in excluded and (c.is_eligible_direct or c in active_vpns)
                ),
                None,
            )

        return None
