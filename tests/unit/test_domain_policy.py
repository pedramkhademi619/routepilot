"""Unit tests for RoutePilot domain and policy models."""

import pytest

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
from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector


def test_traffic_selector_domain_clean_url() -> None:
    """Verifies that URLs entered into domain selectors are automatically stripped to hostname."""
    sel = TrafficSelector(type=SelectorType.DOMAIN, value="https://example.com/api/v1?test=1")
    assert sel.value == "example.com"
    sel.validate_selector()


def test_traffic_selector_cidr_validation() -> None:
    """Validates CIDR subnets."""
    sel = TrafficSelector(type=SelectorType.CIDR, value="192.168.10.0/24")
    sel.validate_selector()

    bad_sel = TrafficSelector(type=SelectorType.CIDR, value="999.999.999.0/24")
    with pytest.raises(ValueError, match="Invalid IP/CIDR"):
        bad_sel.validate_selector()


def test_network_connection_direct_eligibility() -> None:
    """Verifies direct egress eligibility property."""
    conn = NetworkConnection(
        id="Home-WiFi",
        uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        is_vpn=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["192.168.1.173/24"], gateway="192.168.1.1", dns_servers=["192.168.1.1"]
        ),
    )
    assert conn.is_eligible_direct is True
    assert conn.primary_ipv4 == "192.168.1.173"

    vpn_conn = NetworkConnection(
        id="Work-VPN",
        uuid="a3b4c5d6-7e8f-4a1b-8c2d-3e4f5a6b7c8d",
        interface="vpn0",
        kind=ConnectionKind.VPN_GENERIC,
        is_vpn=True,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["10.8.0.2/24"],
            gateway="10.8.0.1",
        ),
    )
    assert vpn_conn.is_eligible_direct is False


def test_routing_rule_priority_sorting() -> None:
    """Verifies deterministic sorting of rules by priority ascending."""
    r1 = RoutingRule(
        name="Rule Low Prio",
        priority=200,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="low.com"),
        action=PolicyAction(type=ActionType.FOLLOW_SYSTEM),
    )
    r2 = RoutingRule(
        name="Rule High Prio",
        priority=10,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="high.com"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    doc = PolicyDocument(updated_at="2026-11-14T10:00:00Z", rules=[r1, r2])
    sorted_rules = doc.sort_by_priority()
    assert sorted_rules[0].name == "Rule High Prio"
    assert sorted_rules[1].name == "Rule Low Prio"


def test_routing_rule_human_summary() -> None:
    """Verifies human-readable plain language explanation of a rule."""
    rule = RoutingRule(
        name="Bypass Bank",
        priority=50,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="bank.example.com"),
        condition=ActivationCondition(type=ConditionType.ANY_VPN_ACTIVE),
        action=PolicyAction(type=ActionType.USE_DIRECT),
        fallback=FallbackPolicy(behavior=FailureBehavior.BLOCK),
    )
    summary = rule.human_summary()
    assert "bank.example.com" in summary
    assert "use direct" in summary
    assert "whenever any VPN is connected" in summary
    assert "blocks traffic" in summary
