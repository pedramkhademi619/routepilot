"""Unit tests for PolicyEngine evaluation, priority overrides, and fail-closed policies."""

from routepilot.application.services.policy_evaluator import PolicyEvaluator
from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.activation_condition import ActivationCondition
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector


def create_mock_connections() -> list[NetworkConnection]:
    """Helper to create realistic mock network connections."""
    wifi = NetworkConnection(
        id="Home-WiFi",
        uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        is_vpn=False,
        is_default=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["192.168.1.173/24"],
            gateway="192.168.1.1",
            dns_servers=["192.168.1.1"],
        ),
    )
    vpn_a = NetworkConnection(
        id="Work-VPN-A",
        uuid="a3b4c5d6-7e8f-4a1b-8c2d-3e4f5a6b7c8d",
        interface="vpn0",
        kind=ConnectionKind.VPN_GENERIC,
        is_vpn=True,
        is_default=True,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["10.8.0.5/24"],
            gateway="10.8.0.1",
            dns_servers=["1.1.1.1"],
        ),
    )
    vpn_b = NetworkConnection(
        id="Cloud-VPN-B",
        uuid="c0ffee00-1234-4abc-9def-00000000beef",
        interface="wg0",
        kind=ConnectionKind.VPN_WIREGUARD,
        is_vpn=True,
        is_default=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["10.100.0.2/24"],
            gateway="10.100.0.1",
            dns_servers=["8.8.8.8"],
        ),
    )
    return [wifi, vpn_a, vpn_b]


def test_cidr_bypass_rule() -> None:
    """Verifies that traffic to an IP in a CIDR subnet bypasses VPN and routes through direct Wi-Fi."""
    connections = create_mock_connections()
    rule = RoutingRule(
        name="Direct Banking CIDR",
        priority=20,
        selector=TrafficSelector(type=SelectorType.CIDR, value="198.51.100.0/24"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    engine = PolicyEvaluator([rule])
    result = engine.evaluate("198.51.100.45", connections)

    assert result.action == ActionType.USE_DIRECT
    assert result.target_connection is not None
    assert result.target_connection.interface == "wlo1"
    assert "Home-WiFi" in result.explanation
    assert not result.is_blocked


def test_priority_override() -> None:
    """Verifies that higher priority (lower number) overrides lower priority rule."""
    connections = create_mock_connections()
    low_prio = RoutingRule(
        name="General VPN Catch-All",
        priority=100,
        selector=TrafficSelector(type=SelectorType.DOMAIN_AND_SUBDOMAINS, value="*.example.com"),
        action=PolicyAction(
            type=ActionType.USE_SELECTED_VPN,
            target_connection_uuid="a3b4c5d6-7e8f-4a1b-8c2d-3e4f5a6b7c8d",
        ),
    )
    high_prio = RoutingRule(
        name="Direct Specific Subdomain",
        priority=10,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="direct.example.com"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    engine = PolicyEvaluator([low_prio, high_prio])

    # Target specific subdomain: should match high priority direct rule
    res1 = engine.evaluate("direct.example.com", connections)
    assert res1.action == ActionType.USE_DIRECT
    assert "Overrode lower-priority rule" in res1.explanation

    # Target other subdomain: should match low priority VPN rule
    res2 = engine.evaluate("other.example.com", connections)
    assert res2.action == ActionType.USE_SELECTED_VPN
    assert res2.target_connection is not None
    assert res2.target_connection.interface == "vpn0"


def test_fail_closed_policy_when_vpn_disconnected() -> None:
    """Verifies that when a required VPN is disconnected, fail-closed policy blocks traffic."""
    wifi_only = [
        NetworkConnection(
            id="Home-WiFi",
            uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
            interface="wlo1",
            kind=ConnectionKind.PHYSICAL_WIFI,
            is_vpn=False,
            state=ConnectionState.ACTIVATED,
            ip4_config=IPConfig(addresses=["192.168.1.173/24"], gateway="192.168.1.1"),
        )
    ]
    rule = RoutingRule(
        name="Corporate Intranet Required VPN",
        priority=10,
        selector=TrafficSelector(type=SelectorType.CIDR, value="10.0.0.0/8"),
        action=PolicyAction(
            type=ActionType.USE_SELECTED_VPN, target_connection_uuid="missing-vpn-uuid"
        ),
        fallback=FallbackPolicy(behavior=FailureBehavior.BLOCK),
    )
    engine = PolicyEvaluator([rule])
    result = engine.evaluate("10.50.1.20", wifi_only)

    assert result.is_blocked is True
    assert result.action == ActionType.BLOCK
    assert "Traffic blocked by fail-closed policy" in result.explanation


def test_activation_condition_vpn_dependent() -> None:
    """Verifies that rules conditional on active VPN do not trigger when VPN is inactive."""
    wifi_only = [
        NetworkConnection(
            id="Home-WiFi",
            uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
            interface="wlo1",
            kind=ConnectionKind.PHYSICAL_WIFI,
            is_vpn=False,
            state=ConnectionState.ACTIVATED,
            ip4_config=IPConfig(addresses=["192.168.1.173/24"], gateway="192.168.1.1"),
        )
    ]
    rule = RoutingRule(
        name="Only Bypass When VPN Active",
        priority=20,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="local-bank.com"),
        condition=ActivationCondition(type=ConditionType.ANY_VPN_ACTIVE),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    engine = PolicyEvaluator([rule])
    result = engine.evaluate("local-bank.com", wifi_only)

    # Condition not met because no VPN is active -> fall back to normal system routing
    assert result.action == ActionType.FOLLOW_SYSTEM
    assert "No explicit RoutePilot rules matched" in result.explanation
