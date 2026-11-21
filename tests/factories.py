"""Reusable domain fixtures for tests."""

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector

WIFI_UUID = "6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab"
VPN_UUID = "a3b4c5d6-7e8f-4a1b-8c2d-3e4f5a6b7c8d"


def wifi(ipv6: bool = False) -> NetworkConnection:
    return NetworkConnection(
        id="Home-WiFi",
        uuid=WIFI_UUID,
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(addresses=["192.168.1.173/24"], gateway="192.168.1.1"),
        ip6_config=(
            IPConfig(addresses=["2001:db8:1::173/64"], gateway="fe80::1") if ipv6 else None
        ),
        metric=600,
    )


def vpn() -> NetworkConnection:
    return NetworkConnection(
        id="Work-VPN",
        uuid=VPN_UUID,
        interface="vpn0",
        kind=ConnectionKind.VPN_GENERIC,
        is_vpn=True,
        is_default=True,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(addresses=["10.8.0.4/24"], gateway="10.8.0.1"),
        metric=50,
    )


def rule(
    name: str,
    value: str,
    selector: SelectorType = SelectorType.CIDR,
    action: ActionType = ActionType.USE_DIRECT,
    priority: int = 50,
    fallback: FailureBehavior = FailureBehavior.BLOCK,
    target: str | None = None,
) -> RoutingRule:
    return RoutingRule(
        name=name,
        priority=priority,
        selector=TrafficSelector(type=selector, value=value),
        action=PolicyAction(type=action, target_connection_uuid=target),
        fallback=FallbackPolicy(behavior=fallback),
    )
