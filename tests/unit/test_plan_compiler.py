"""Unit tests for PlanCompiler generating declarative kernel plans."""

from factories import VPN_UUID, rule, vpn, wifi

from routepilot.application.services.plan_compiler import PlanCompiler
from routepilot.application.services.routing_layout import RoutingLayout
from routepilot.domain.models.route_type import RouteType
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.selector_type import SelectorType

OVERRIDE = RoutingLayout.OVERRIDE_TABLE
GUARD = RoutingLayout.GUARD_TABLE


def _routes(plan, table, route_type=RouteType.UNICAST):  # type: ignore[no-untyped-def]
    return {
        r.destination: r for r in plan.routes if r.table_id == table and r.route_type == route_type
    }


def test_direct_cidr_rule_routes_via_physical_gateway() -> None:
    plan = PlanCompiler().compile([rule("Bank", "198.51.100.0/24")], [wifi(), vpn()])

    route = _routes(plan, OVERRIDE)["198.51.100.0/24"]
    assert route.gateway == "192.168.1.1"
    assert route.interface == "wlo1"
    # Fail-closed by default: a guard catches the destination if wlo1 disappears.
    assert "198.51.100.0/24" in _routes(plan, GUARD, RouteType.UNREACHABLE)
    assert {(r.priority, r.table_id, r.family) for r in plan.rules} == {
        (RoutingLayout.OVERRIDE_PRIORITY, OVERRIDE, 4),
        (RoutingLayout.GUARD_PRIORITY, GUARD, 4),
    }
    assert plan.nft_ruleset is None


def test_domain_rule_uses_resolved_addresses_and_split_dns() -> None:
    compiler = PlanCompiler()
    rules = [rule("Local site", "*.example.ir", selector=SelectorType.DOMAIN_AND_SUBDOMAINS)]

    requests = compiler.resolution_requests(rules, [wifi(), vpn()])
    assert requests == {"example.ir": "wlo1", "www.example.ir": "wlo1"}

    plan = compiler.compile(
        rules,
        [wifi(), vpn()],
        {"example.ir": ["203.0.113.7"], "www.example.ir": ["203.0.113.7", "203.0.113.8"]},
    )
    assert set(_routes(plan, OVERRIDE)) == {"203.0.113.7/32", "203.0.113.8/32"}
    assert plan.split_dns == {"wlo1": ["example.ir"]}


def test_unresolvable_domain_produces_warning_not_routes() -> None:
    plan = PlanCompiler().compile(
        [rule("Ghost", "nothing.invalid", selector=SelectorType.DOMAIN)], [wifi()], {}
    )
    assert plan.routes == []
    assert any("could not resolve" in w for w in plan.warnings)


def test_selected_vpn_routes_by_device_only() -> None:
    plan = PlanCompiler().compile(
        [rule("Intranet", "10.20.0.0/16", action=ActionType.USE_SELECTED_VPN, target=VPN_UUID)],
        [wifi(), vpn()],
    )
    route = _routes(plan, OVERRIDE)["10.20.0.0/16"]
    assert route.interface == "vpn0"
    assert route.gateway is None


def test_fail_closed_when_target_missing_only_installs_guard() -> None:
    plan = PlanCompiler().compile(
        [rule("Intranet", "10.20.0.0/16", action=ActionType.USE_SELECTED_VPN, target=VPN_UUID)],
        [wifi()],
    )
    assert _routes(plan, OVERRIDE) == {}
    assert "10.20.0.0/16" in _routes(plan, GUARD, RouteType.UNREACHABLE)
    assert any("fail-closed" in line for line in plan.summary_lines)


def test_fail_open_when_target_missing_leaves_traffic_alone() -> None:
    plan = PlanCompiler().compile(
        [rule("Optional", "10.20.0.0/16", fallback=FailureBehavior.FOLLOW_SYSTEM)], [vpn()]
    )
    assert plan.routes == []
    assert plan.rules == []


def test_explicit_block_generates_idempotent_nft_table() -> None:
    plan = PlanCompiler().compile(
        [
            rule("Ads", "203.0.113.0/24", action=ActionType.BLOCK),
            rule("Ads6", "2001:db8:dead::/48", action=ActionType.BLOCK),
        ],
        [wifi()],
    )
    assert plan.nft_ruleset is not None
    assert "table inet routepilot" in plan.nft_ruleset
    assert "elements = { 203.0.113.0/24 }" in plan.nft_ruleset
    assert "elements = { 2001:db8:dead::/48 }" in plan.nft_ruleset
    assert "ip daddr @block_v4 reject" in plan.nft_ruleset
    assert plan.routes == []


def test_higher_priority_rule_claims_shared_destination() -> None:
    rules = [
        rule("Low", "203.0.113.5", selector=SelectorType.IP_ADDRESS, priority=90),
        rule(
            "High",
            "203.0.113.5",
            selector=SelectorType.IP_ADDRESS,
            priority=10,
            action=ActionType.FOLLOW_SYSTEM,
        ),
    ]
    plan = PlanCompiler().compile(rules, [wifi(), vpn()])

    assert "203.0.113.5/32" in _routes(plan, OVERRIDE, RouteType.THROW)
    assert _routes(plan, OVERRIDE) == {}
    assert any("already claimed" in w for w in plan.warnings)


def test_ipv6_destination_uses_ipv6_gateway_and_rule() -> None:
    plan = PlanCompiler().compile([rule("v6", "2001:db8:beef::/48")], [wifi(ipv6=True), vpn()])
    route = _routes(plan, OVERRIDE)["2001:db8:beef::/48"]
    assert route.family == 6
    assert route.gateway == "fe80::1"
    assert (RoutingLayout.OVERRIDE_PRIORITY, 6) in {(r.priority, r.family) for r in plan.rules}


def test_ipv6_destination_without_ipv6_gateway_is_reported() -> None:
    plan = PlanCompiler().compile([rule("v6", "2001:db8:beef::/48")], [wifi()])
    assert _routes(plan, OVERRIDE) == {}
    assert any("no IPv6 gateway" in w for w in plan.warnings)


def test_disabled_and_application_rules_are_not_compiled() -> None:
    disabled = rule("Off", "198.51.100.0/24")
    disabled.enabled = False
    app = rule("App", "firefox", selector=SelectorType.APPLICATION)
    plan = PlanCompiler().compile([disabled, app], [wifi()])
    assert plan.routes == []
    assert any("per-application" in w for w in plan.warnings)


def test_vpn_route_never_captures_its_own_server_endpoint() -> None:
    tunnel = vpn()
    tunnel.server_endpoint = "203.0.113.50"
    plan = PlanCompiler().compile(
        [
            rule(
                "All via VPN", "203.0.113.0/24", action=ActionType.USE_SELECTED_VPN, target=VPN_UUID
            )
        ],
        [wifi(), tunnel],
    )
    assert _routes(plan, OVERRIDE) == {}
    assert any("would loop" in w for w in plan.warnings)
