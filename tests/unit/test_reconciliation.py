"""Unit tests for ReconciliationService diffing, journaling and rollback."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from factories import rule, wifi

from routepilot.application.services.plan_compiler import PlanCompiler
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.application.services.routing_layout import RoutingLayout
from routepilot.domain.exceptions.rollback_error import RollbackError
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.ports.dns_resolver_port import DnsResolverPort
from routepilot.domain.ports.firewall_port import FirewallPort
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort
from routepilot.infrastructure.adapters.json_plan_journal_adapter import JsonPlanJournalAdapter


class FakeRouting(PolicyRoutingPort):
    """In-memory kernel: just enough behaviour to observe convergence."""

    def __init__(self) -> None:
        self.routes: dict[tuple[int, int, str], RouteEntry] = {}
        self.rules: dict[tuple[int, int], int] = {}

    def replace_route(self, route: RouteEntry) -> None:
        self.routes[route.key] = route

    def delete_route(self, route: RouteEntry) -> None:
        self.routes.pop(route.key, None)

    def list_routes(self, table_id: int, family: int = 4) -> list[RouteEntry]:
        return [r for k, r in self.routes.items() if k[0] == table_id and k[1] == family]

    def flush_table(self, table_id: int, family: int = 4) -> None:
        for route in self.list_routes(table_id, family):
            self.delete_route(route)

    def replace_rule(self, rule) -> None:  # type: ignore[no-untyped-def]
        self.rules[(rule.priority, rule.family)] = rule.table_id

    def delete_rule(self, priority: int, family: int = 4) -> None:
        self.rules.pop((priority, family), None)


def _service(tmp_path: Path, routing: PolicyRoutingPort | None = None):  # type: ignore[no-untyped-def]
    firewall = MagicMock(spec=FirewallPort)
    dns = MagicMock(spec=DnsResolverPort)
    journal = JsonPlanJournalAdapter(tmp_path / "journal.json")
    service = ReconciliationService(routing or FakeRouting(), firewall, dns, journal)
    return service, firewall, dns, journal


def test_apply_converges_and_commits(tmp_path: Path) -> None:
    routing = FakeRouting()
    service, firewall, _, journal = _service(tmp_path, routing)
    plan = PlanCompiler().compile([rule("Direct", "198.51.100.0/24")], [wifi()])

    assert service.apply_plan(plan) is True
    assert {r.destination for r in routing.routes.values()} == {"198.51.100.0/24"}
    assert routing.rules == {
        (RoutingLayout.OVERRIDE_PRIORITY, 4): RoutingLayout.OVERRIDE_TABLE,
        (RoutingLayout.GUARD_PRIORITY, 4): RoutingLayout.GUARD_TABLE,
    }
    firewall.flush_routepilot_table.assert_called_once()  # no block rules -> no nft table
    loaded = journal.load()
    assert loaded is not None and loaded.plan_id == plan.plan_id


def test_reapply_removes_stale_routes_and_rules(tmp_path: Path) -> None:
    routing = FakeRouting()
    service, *_ = _service(tmp_path, routing)
    compiler = PlanCompiler()
    service.apply_plan(compiler.compile([rule("A", "198.51.100.0/24")], [wifi()]))

    service.apply_plan(compiler.compile([], [wifi()]))

    assert routing.routes == {}
    assert routing.rules == {}


def test_split_dns_follows_plan_changes(tmp_path: Path) -> None:
    service, _, dns, _ = _service(tmp_path)
    compiler = PlanCompiler()
    domain_rule = rule("Site", "example.ir", selector=SelectorType.DOMAIN)

    service.apply_plan(compiler.compile([domain_rule], [wifi()], {"example.ir": ["203.0.113.7"]}))
    dns.configure_split_dns.assert_called_once_with("wlo1", ["example.ir"], None)

    service.apply_plan(compiler.compile([], [wifi()]))
    dns.reset_split_dns.assert_called_once_with("wlo1", ["example.ir"])


def test_failure_rolls_back_everything(tmp_path: Path) -> None:
    routing = FakeRouting()
    service, firewall, _, journal = _service(tmp_path, routing)
    firewall.apply_ruleset.side_effect = RuntimeError("Kernel permission denied")
    plan = PlanCompiler().compile(
        [rule("Direct", "198.51.100.0/24"), rule("Ads", "203.0.113.0/24", action=ActionType.BLOCK)],
        [wifi()],
    )

    with pytest.raises(RollbackError):
        service.apply_plan(plan)

    firewall.flush_routepilot_table.assert_called_once()
    assert routing.routes == {}
    assert journal.load() is None


def test_emergency_reset_removes_owned_and_legacy_rules(tmp_path: Path) -> None:
    routing = MagicMock(spec=PolicyRoutingPort)
    service, firewall, *_ = _service(tmp_path, routing)

    service.emergency_reset()

    deleted = {call.args for call in routing.delete_rule.call_args_list}
    assert (RoutingLayout.OVERRIDE_PRIORITY, 6) in deleted
    assert (RoutingLayout.LEGACY_RULE_PRIORITIES[0], 4) in deleted
    flushed = {call.args for call in routing.flush_table.call_args_list}
    assert (RoutingLayout.GUARD_TABLE, 4) in flushed
    firewall.flush_routepilot_table.assert_called_once()
