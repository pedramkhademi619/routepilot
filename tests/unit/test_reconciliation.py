"""Unit tests for ReconciliationService transactional apply and rollback."""

from unittest.mock import MagicMock

import pytest

from routepilot.application.services.plan_compiler import PlanCompiler
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.exceptions.rollback_error import RollbackError
from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector
from routepilot.domain.ports.firewall_port import FirewallPort
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort


def test_reconciliation_applies_plan_and_commits(tmp_path: str) -> None:
    mock_routing = MagicMock(spec=PolicyRoutingPort)
    mock_firewall = MagicMock(spec=FirewallPort)
    journal_file = f"{tmp_path}/test_journal.json"

    service = ReconciliationService(mock_routing, mock_firewall, journal_path=journal_file)

    wifi = NetworkConnection(
        id="Home-WiFi",
        uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        is_vpn=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(addresses=["192.168.1.173/24"], gateway="192.168.1.1"),
    )
    rule = RoutingRule(
        name="Direct IP",
        priority=10,
        selector=TrafficSelector(type=SelectorType.CIDR, value="198.51.100.0/24"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    plan = PlanCompiler().compile([rule], [wifi])

    success = service.apply_plan(plan)
    assert success is True

    mock_firewall.apply_ruleset.assert_called_once_with(plan.nft_ruleset_content)
    mock_routing.add_routing_table_route.assert_called_once()
    mock_routing.add_policy_rule.assert_called_once()


def test_reconciliation_rolls_back_on_failure(tmp_path: str) -> None:
    mock_routing = MagicMock(spec=PolicyRoutingPort)
    mock_firewall = MagicMock(spec=FirewallPort)
    mock_firewall.apply_ruleset.side_effect = RuntimeError("Kernel permission denied")
    journal_file = f"{tmp_path}/test_journal.json"

    service = ReconciliationService(mock_routing, mock_firewall, journal_path=journal_file)

    wifi = NetworkConnection(
        id="Home-WiFi",
        uuid="6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab",
        interface="wlo1",
        kind=ConnectionKind.PHYSICAL_WIFI,
        is_vpn=False,
        state=ConnectionState.ACTIVATED,
        ip4_config=IPConfig(addresses=["192.168.1.173/24"], gateway="192.168.1.1"),
    )
    rule = RoutingRule(
        name="Direct IP",
        priority=10,
        selector=TrafficSelector(type=SelectorType.CIDR, value="198.51.100.0/24"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    plan = PlanCompiler().compile([rule], [wifi])

    with pytest.raises(RollbackError):
        service.apply_plan(plan)

    # Rollback must flush routepilot table
    mock_firewall.flush_routepilot_table.assert_called_once()
