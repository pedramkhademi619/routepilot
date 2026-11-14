"""PyQt6 UI tests using pytest-qt and offscreen platform."""

import pytest

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.ui.views.main_window import MainWindow


@pytest.fixture
def mock_app(qtbot: pytest.FixtureRequest, tmp_path: str) -> MainWindow:
    """Fixture providing an initialized MainWindow with isolated test adapters."""
    policy_file = f"{tmp_path}/test_policy.json"
    journal_file = f"{tmp_path}/test_journal.json"

    import asyncio

    discovery_adapter = MockDiscoveryAdapter()
    discovery_service = DiscoveryService(discovery_adapter)
    asyncio.run(discovery_service.refresh())
    policy_repo = JsonPolicyRepositoryAdapter(file_path=policy_file)

    # Use dummy objects for privileged adapters
    from unittest.mock import MagicMock

    from routepilot.domain.ports.firewall_port import FirewallPort
    from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

    routing_port = MagicMock(spec=PolicyRoutingPort)
    firewall_port = MagicMock(spec=FirewallPort)
    reconciliation = ReconciliationService(routing_port, firewall_port, journal_path=journal_file)

    window = MainWindow(
        discovery_service=discovery_service,
        policy_repo=policy_repo,
        reconciliation_service=reconciliation,
        on_theme_changed=lambda t: None,
    )
    qtbot.addWidget(window)
    return window


def test_main_window_tabs_navigation(mock_app: MainWindow) -> None:
    """Verifies that navigation buttons correctly switch stacked screens."""
    assert mock_app.stack.currentIndex() == 0  # Overview

    mock_app.switch_to_tab(1)
    assert mock_app.stack.currentIndex() == 1  # Rules

    mock_app.switch_to_tab(2)
    assert mock_app.stack.currentIndex() == 2  # Connections

    mock_app.switch_to_tab(3)
    assert mock_app.stack.currentIndex() == 3  # Diagnostics

    mock_app.switch_to_tab(4)
    assert mock_app.stack.currentIndex() == 4  # Settings


def test_rules_view_add_and_render(mock_app: MainWindow) -> None:
    """Verifies that adding a rule updates the table in RulesView."""
    rule = RoutingRule(
        name="Test Bypass Rule",
        priority=25,
        selector=TrafficSelector(type=SelectorType.DOMAIN, value="test.example.com"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    mock_app.rules_vm.save_or_update_rule(rule)

    rules = mock_app.rules_vm.get_rules()
    assert len(rules) == 1
    assert rules[0].name == "Test Bypass Rule"
    assert mock_app.rules_view.table.rowCount() == 1


def test_diagnostics_view_evaluation(mock_app: MainWindow) -> None:
    """Verifies that running diagnostics simulation renders the evaluation result."""
    rule = RoutingRule(
        name="Banking Bypass",
        priority=10,
        selector=TrafficSelector(type=SelectorType.CIDR, value="198.51.100.0/24"),
        action=PolicyAction(type=ActionType.USE_DIRECT),
    )
    mock_app.rules_vm.save_or_update_rule(rule)

    res = mock_app.diagnostics_vm.evaluate_target("198.51.100.10")
    assert res.action == ActionType.USE_DIRECT
    assert "Banking Bypass" in res.explanation


def test_rules_table_responsiveness(mock_app: MainWindow) -> None:
    """Verifies that the rules table has responsive column stretch and fixed controls."""
    header = mock_app.rules_view.table.horizontalHeader()
    from PyQt6.QtWidgets import QHeaderView

    # Verify stretchLastSection is disabled so controls don't stretch indefinitely
    assert not header.stretchLastSection()
    # Verify Target Selector (col 3) stretches across all available space
    assert header.sectionResizeMode(3) == QHeaderView.ResizeMode.Stretch
    # Verify Controls (col 6) has fixed width
    assert header.sectionResizeMode(6) == QHeaderView.ResizeMode.Fixed
    assert mock_app.rules_view.table.columnWidth(6) == 220


def test_persian_language_switching(mock_app: MainWindow) -> None:
    """Verifies that switching to Persian translates navigation tabs and settings."""
    from routepilot.ui.translation_manager import TranslationManager

    i18n = TranslationManager.instance()

    # Switch to Persian
    mock_app.settings_vm.set_language("fa")
    assert i18n.current_language == "fa"
    assert mock_app.nav_buttons[0].text() == "نمای کلی"
    assert mock_app.nav_buttons[1].text() == "قوانین ترافیک"
    assert mock_app.nav_buttons[4].text() == "تنظیمات"

    # Switch back to English
    mock_app.settings_vm.set_language("en")
    assert i18n.current_language == "en"
    assert mock_app.nav_buttons[0].text() == "Overview"
    assert mock_app.nav_buttons[1].text() == "Traffic Rules"
    assert mock_app.nav_buttons[4].text() == "Settings"

