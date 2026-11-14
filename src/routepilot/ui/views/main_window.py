"""Main application window for RoutePilot."""

import asyncio
import subprocess
from collections.abc import Callable

from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.connections_viewmodel import ConnectionsViewModel
from routepilot.ui.viewmodels.diagnostics_viewmodel import DiagnosticsViewModel
from routepilot.ui.viewmodels.overview_viewmodel import OverviewViewModel
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel
from routepilot.ui.viewmodels.settings_viewmodel import SettingsViewModel
from routepilot.ui.views.connections_view import ConnectionsView
from routepilot.ui.views.diagnostics_view import DiagnosticsView
from routepilot.ui.views.overview_view import OverviewView
from routepilot.ui.views.rule_editor_dialog import RuleEditorDialog
from routepilot.ui.views.rules_view import RulesView
from routepilot.ui.views.settings_view import SettingsView
from routepilot.ui.views.tray_icon_manager import TrayIconManager


class MainWindow(QMainWindow):
    """Primary application window hosting navigation bar and view screens."""

    def __init__(
        self,
        discovery_service: DiscoveryService,
        policy_repo: PolicyRepositoryPort,
        reconciliation_service: ReconciliationService,
        on_theme_changed: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.discovery_service = discovery_service
        self.policy_repo = policy_repo
        self.reconciliation_service = reconciliation_service
        self.on_theme_changed = on_theme_changed
        self.i18n = TranslationManager.instance()

        self.setWindowTitle(self.i18n.t("app.title"))
        self.resize(1020, 680)
        self.setMinimumSize(850, 550)

        # Initialize ViewModels
        self.overview_vm = OverviewViewModel(self.discovery_service, self.policy_repo)
        self.rules_vm = RulesViewModel(self.policy_repo)
        self.connections_vm = ConnectionsViewModel(self.discovery_service)
        self.diagnostics_vm = DiagnosticsViewModel(self.discovery_service, self.policy_repo)
        self.settings_vm = SettingsViewModel(self.policy_repo, self.reconciliation_service)
        self.settings_vm.theme_changed.connect(self.on_theme_changed)

        self.nav_buttons: dict[int, QPushButton] = {}
        self._setup_ui()
        self._init_tray()

        self.i18n.language_changed.connect(lambda _: self.retranslate_ui())
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Navigation Sidebar
        nav_frame = QFrame()
        nav_frame.setObjectName("navBar")
        nav_frame.setFixedWidth(210)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 20, 8, 20)
        nav_layout.setSpacing(6)

        # Brand header
        brand_box = QHBoxLayout()
        brand_box.setContentsMargins(12, 0, 12, 16)
        logo_label = QLabel("RoutePilot")
        logo_label.setObjectName("titleLabel")
        brand_box.addWidget(logo_label)
        brand_box.addStretch()
        nav_layout.addLayout(brand_box)

        # Nav button group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("nav.overview", 0),
            ("nav.rules", 1),
            ("nav.connections", 2),
            ("nav.diagnostics", 3),
            ("nav.settings", 4),
        ]

        for key, index in nav_items:
            btn = QPushButton(self.i18n.t(key))
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            if index == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, index)
            self.nav_buttons[index] = btn
            nav_layout.addWidget(btn)

        self.nav_group.idClicked.connect(self._on_nav_clicked)
        nav_layout.addStretch()

        main_layout.addWidget(nav_frame)

        # Central Stacked Views
        self.stack = QStackedWidget()

        self.overview_view = OverviewView(
            self.overview_vm, on_navigate_rules=lambda: self.switch_to_tab(1)
        )
        self.rules_view = RulesView(self.rules_vm, on_edit_rule=self._open_rule_editor)
        self.connections_view = ConnectionsView(
            self.connections_vm, on_refresh=self._trigger_refresh
        )
        self.diagnostics_view = DiagnosticsView(self.diagnostics_vm)
        self.settings_view = SettingsView(self.settings_vm)

        self.stack.addWidget(self.overview_view)
        self.stack.addWidget(self.rules_view)
        self.stack.addWidget(self.connections_view)
        self.stack.addWidget(self.diagnostics_view)
        self.stack.addWidget(self.settings_view)

        main_layout.addWidget(self.stack)
        self.setCentralWidget(central_widget)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates window title, navigation bar, and child views."""
        t = self.i18n.t
        self.setWindowTitle(t("app.title"))

        if 0 in self.nav_buttons:
            self.nav_buttons[0].setText(t("nav.overview"))
        if 1 in self.nav_buttons:
            self.nav_buttons[1].setText(t("nav.rules"))
        if 2 in self.nav_buttons:
            self.nav_buttons[2].setText(t("nav.connections"))
        if 3 in self.nav_buttons:
            self.nav_buttons[3].setText(t("nav.diagnostics"))
        if 4 in self.nav_buttons:
            self.nav_buttons[4].setText(t("nav.settings"))

        # Notify child views
        if hasattr(self.overview_view, "retranslate_ui"):
            self.overview_view.retranslate_ui()
        if hasattr(self.rules_view, "retranslate_ui"):
            self.rules_view.retranslate_ui()
        if hasattr(self.connections_view, "retranslate_ui"):
            self.connections_view.retranslate_ui()
        if hasattr(self.diagnostics_view, "retranslate_ui"):
            self.diagnostics_view.retranslate_ui()
        if hasattr(self.settings_view, "retranslate_ui"):
            self.settings_view.retranslate_ui()

    def _init_tray(self) -> None:
        self.tray_manager = TrayIconManager(
            on_toggle_window=self._toggle_visibility,
            on_open_rules=self._on_tray_open_rules,
            on_quit=self._on_tray_quit,
        )

    def _on_tray_open_rules(self) -> None:
        self.show()
        self.switch_to_tab(1)

    def _on_tray_quit(self) -> None:
        self.close()

    def switch_to_tab(self, index: int) -> None:
        """Switches current stacked screen and syncs nav button state."""
        self.stack.setCurrentIndex(index)
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)

    def _on_nav_clicked(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _open_rule_editor(self, rule: RoutingRule | None) -> None:
        dialog = RuleEditorDialog(existing_rule=rule, parent=self)
        if dialog.exec() == RuleEditorDialog.DialogCode.Accepted:
            saved = dialog.get_rule()
            if saved:
                self.rules_vm.save_or_update_rule(saved)
                self.overview_vm.refresh()
                subprocess.Popen(["/home/pedram/.local/bin/routepilot-apply"])

    def _trigger_refresh(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.discovery_service.refresh())
            else:
                loop.run_until_complete(self.discovery_service.refresh())
        except Exception:
            pass

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
