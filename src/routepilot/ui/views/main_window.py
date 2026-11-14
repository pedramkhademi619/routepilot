"""Main application window for RoutePilot."""

import asyncio

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
        on_theme_changed: callable,
    ) -> None:
        super().__init__()
        self.discovery_service = discovery_service
        self.policy_repo = policy_repo
        self.reconciliation_service = reconciliation_service
        self.on_theme_changed = on_theme_changed

        self.setWindowTitle("RoutePilot — Traffic Policy Routing")
        self.resize(980, 680)
        self.setMinimumSize(850, 550)

        # Initialize ViewModels
        self.overview_vm = OverviewViewModel(self.discovery_service, self.policy_repo)
        self.rules_vm = RulesViewModel(self.policy_repo)
        self.connections_vm = ConnectionsViewModel(self.discovery_service)
        self.diagnostics_vm = DiagnosticsViewModel(self.discovery_service, self.policy_repo)
        self.settings_vm = SettingsViewModel(self.policy_repo, self.reconciliation_service)
        self.settings_vm.theme_changed.connect(self.on_theme_changed)

        self._setup_ui()
        self._init_tray()

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
            ("Overview", 0),
            ("Traffic Rules", 1),
            ("Connections", 2),
            ("Diagnostics", 3),
            ("Settings", 4),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            if index == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, index)
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

    def _init_tray(self) -> None:
        self.tray_manager = TrayIconManager(
            on_toggle_window=self._toggle_visibility,
            on_open_rules=lambda: (self.show(), self.switch_to_tab(1)),
            on_quit=self.close,
        )

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
