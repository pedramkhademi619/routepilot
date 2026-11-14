"""Unit tests for PlanCompiler generating atomic execution plans."""

from routepilot.application.services.plan_compiler import PlanCompiler
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


def test_plan_compiler_generates_direct_routing_and_nftables() -> None:
    wifi = NetworkConnection(
        id="Home-WiFi",
        uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        is_vpn=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(
            addresses=["192.168.1.173/24"],
            gateway="192.168.1.1",
        ),
    )
    rule = RoutingRule(
        name="Direct IP Bypass",
        priority=10,
        selector=TrafficSelector(type=SelectorType.CIDR, value="198.51.100.0/24"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )

    compiler = PlanCompiler()
    plan = compiler.compile([rule], [wifi])

    assert plan.plan_id is not None
    assert 10001 in plan.tables_to_create
    assert plan.tables_to_create[10001].gateway == "192.168.1.1"
    assert plan.tables_to_create[10001].interface == "wlo1"

    # Check nftables ruleset
    assert "table inet routepilot" in plan.nft_ruleset_content
    assert "198.51.100.0/24" in plan.nft_ruleset_content
    assert "type route hook output priority mangle" in plan.nft_ruleset_content
    assert "meta mark set 0x10" in plan.nft_ruleset_content

    # Check rollback
    assert 10001 in plan.rollback_tables
    assert 10010 in plan.rollback_rule_priorities


def test_plan_compiler_fail_closed_block_generation() -> None:
    # No direct connection available
    rule = RoutingRule(
        name="Corporate Block on Disconnect",
        priority=5,
        selector=TrafficSelector(type=SelectorType.CIDR, value="10.200.0.0/16"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
        fallback=FallbackPolicy(behavior=FailureBehavior.BLOCK),
    )

    compiler = PlanCompiler()
    plan = compiler.compile([rule], [])

    assert "table inet routepilot" in plan.nft_ruleset_content
    assert "10.200.0.0/16" in plan.nft_ruleset_content
    assert "ip daddr @block_v4 drop" in plan.nft_ruleset_content
