"""PyQt6 UI tests using pytest-qt and the offscreen platform."""

import asyncio
import sys
from pathlib import Path

import pytest
from factories import VPN_UUID, rule, vpn, wifi
from PyQt6.QtWidgets import QApplication, QLabel
from pytestqt.qtbot import QtBot

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.ui.controllers.privileged_helper import PrivilegedHelper
from routepilot.ui.style import ThemeManager
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.views.main_window import MainWindow
from routepilot.ui.views.rule_editor_dialog import RuleEditorDialog


class RecordingHelper(PrivilegedHelper):
    """Privileged helper that records requests instead of running pkexec."""

    def __init__(self, policy_path: Path) -> None:
        super().__init__(policy_path)
        self.requests: list[str] = []

    def _request(self, command: str) -> None:
        self.requests.append(command)


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path) -> MainWindow:
    TranslationManager.instance().set_language("en")
    discovery_service = DiscoveryService(MockDiscoveryAdapter([wifi(), vpn()]))
    asyncio.run(discovery_service.refresh())
    repo = JsonPolicyRepositoryAdapter(tmp_path / "policy.json")
    win = MainWindow(
        discovery_service=discovery_service,
        policy_repo=repo,
        helper=RecordingHelper(repo.file_path),
        theme_manager=ThemeManager(),
    )
    qtbot.addWidget(win)
    return win


def test_navigation_switches_pages(window: MainWindow) -> None:
    for index in range(5):
        window.switch_to_tab(index)
        assert window.stack.currentIndex() == index
        assert window.nav_buttons[index].isChecked()


def test_saving_a_rule_renders_it_and_triggers_apply(window: MainWindow) -> None:
    window.rules_vm.save_or_update_rule(rule("Test Bypass", "198.51.100.0/24"))

    assert window.rules_view.table.rowCount() == 1
    assert window.rules_view.stack.currentWidget() is window.rules_view.table
    assert window.helper.requests == ["apply"]  # type: ignore[attr-defined]


def test_empty_state_and_filter_feedback(window: MainWindow) -> None:
    view = window.rules_view
    assert view.stack.currentWidget() is view.empty_state
    window.rules_vm.save_or_update_rule(rule("Bank", "198.51.100.0/24"))
    view.search_input.setText("does-not-exist")
    assert view.stack.currentWidget() is view.empty_state
    assert "does-not-exist" in view.empty_title.text()


def test_diagnostics_evaluation(window: MainWindow) -> None:
    window.rules_vm.save_or_update_rule(rule("Banking Bypass", "198.51.100.0/24", priority=10))
    res = window.diagnostics_vm.evaluate_target("198.51.100.10")
    assert res.action == ActionType.USE_DIRECT
    assert "Banking Bypass" in res.explanation
    assert window.diagnostics_view.result_title.property("state") == "routed"


def test_no_raw_translation_keys_are_displayed(window: MainWindow) -> None:
    """Regression: some pages used QObject.tr() and showed keys like 'settings.title'."""
    for lang in ("en", "fa"):
        TranslationManager.instance().set_language(lang)
        for page in window.pages:
            for label in page.findChildren(QLabel):
                text = label.text()
                assert not (
                    text.count(".") == 1
                    and text.replace(".", "").replace("_", "").isalpha()
                    and text.islower()
                ), text
    TranslationManager.instance().set_language("en")


def test_persian_switches_layout_direction(window: MainWindow) -> None:
    window.settings_vm.set_language("fa")
    app = QApplication.instance()
    assert isinstance(app, QApplication) and app.isRightToLeft()
    assert "مسیریابی" in window.windowTitle()
    window.settings_vm.set_language("en")
    assert app.isLeftToRight()


@pytest.mark.parametrize("width", [480, 640, 900, 1280])
def test_window_never_needs_horizontal_scroll(window: MainWindow, qtbot: QtBot, width: int) -> None:
    window.rules_vm.save_or_update_rule(
        rule("A rule with a fairly long descriptive name", "198.51.100.0/24")
    )
    window.show()
    window.resize(width, 640)
    qtbot.wait(50)
    for index, page in enumerate(window.pages):
        window.switch_to_tab(index)
        qtbot.wait(10)
        assert page.minimumSizeHint().width() <= window.stack.width(), type(page).__name__


def test_sidebar_collapses_and_columns_hide_when_narrow(window: MainWindow, qtbot: QtBot) -> None:
    window.rules_vm.save_or_update_rule(rule("Bank", "198.51.100.0/24"))
    window.show()
    window.switch_to_tab(1)

    window.resize(1280, 700)
    qtbot.wait(50)
    assert window.nav_frame.width() == MainWindow.NAV_WIDTH
    assert window.nav_buttons[0].text().strip() == "Overview"
    table = window.rules_view.table
    assert not table.isColumnHidden(window.rules_view.COL_CONDITION)

    window.resize(520, 700)
    qtbot.wait(50)
    assert window.nav_frame.width() == MainWindow.NAV_WIDTH_COMPACT
    assert window.nav_buttons[0].text() == ""
    assert window.nav_buttons[0].toolTip() == "Overview"
    assert table.isColumnHidden(window.rules_view.COL_CONDITION)
    assert table.isColumnHidden(window.rules_view.COL_ACTION)
    window.switch_to_tab(0)
    qtbot.wait(50)
    assert window.overview_view.stats_row.is_stacked


def test_rule_editor_offers_vpn_choice_for_vpn_rules(window: MainWindow) -> None:
    dialog = RuleEditorDialog(existing_rule=None, vpns=[vpn()], parent=window)
    dialog.name_input.setText("Intranet")
    dialog.selector_combo.setCurrentIndex(dialog.selector_combo.findData(SelectorType.CIDR))
    dialog.value_input.setText("10.20.0.0/16")
    dialog.action_combo.setCurrentIndex(dialog.action_combo.findData(ActionType.USE_SELECTED_VPN))
    dialog.vpn_combo.setCurrentIndex(dialog.vpn_combo.findData(VPN_UUID))

    assert not dialog.vpn_combo.isHidden()
    built = dialog.viewmodel.build_rule()
    assert built.action.target_connection_uuid == VPN_UUID


def test_rule_editor_requires_vpn_for_specific_vpn_condition(window: MainWindow) -> None:
    dialog = RuleEditorDialog(existing_rule=None, vpns=[], parent=window)
    dialog.name_input.setText("Needs VPN")
    dialog.value_input.setText("example.com")
    dialog.condition_combo.setCurrentIndex(
        dialog.condition_combo.findData(ConditionType.SPECIFIC_VPN_ACTIVE)
    )
    assert dialog.save_btn is not None and not dialog.save_btn.isEnabled()
    assert "VPN" in dialog.error_label.text()


def test_editing_keeps_rule_identity(window: MainWindow) -> None:
    existing = rule("Existing Rule", "example.com", selector=SelectorType.DOMAIN, priority=10)
    dialog = RuleEditorDialog(existing_rule=existing, parent=window)
    assert dialog.name_input.text() == "Existing Rule"
    assert dialog.viewmodel.build_rule().id == existing.id


def test_privileged_helper_passes_policy_path(tmp_path: Path) -> None:
    helper = PrivilegedHelper(tmp_path / "policy.json")
    argv = helper.command_for("apply")
    assert argv[:3] == [sys.executable, "-m", "routepilot"]
    assert argv[-3:] == ["--policy", str(tmp_path / "policy.json"), "apply"]
