"""Main application window for RoutePilot."""

from datetime import datetime

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QCloseEvent, QIcon, QResizeEvent
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
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort
from routepilot.ui.controllers.discovery_refresher import DiscoveryRefresher
from routepilot.ui.controllers.privileged_helper import PrivilegedHelper
from routepilot.ui.icons import Icons
from routepilot.ui.style import ThemeManager
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.connections_viewmodel import ConnectionsViewModel
from routepilot.ui.viewmodels.diagnostics_viewmodel import DiagnosticsViewModel
from routepilot.ui.viewmodels.overview_viewmodel import OverviewViewModel
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel
from routepilot.ui.viewmodels.settings_viewmodel import SettingsViewModel
from routepilot.ui.views.base_page import BasePage
from routepilot.ui.views.connections_view import ConnectionsView
from routepilot.ui.views.diagnostics_view import DiagnosticsView
from routepilot.ui.views.overview_view import OverviewView
from routepilot.ui.views.rule_editor_dialog import RuleEditorDialog
from routepilot.ui.views.rules_view import RulesView
from routepilot.ui.views.settings_view import SettingsView
from routepilot.ui.views.tray_icon_manager import TrayIconManager


class MainWindow(QMainWindow):
    """Primary window: navigation sidebar, stacked pages and a status bar."""

    NAV_ITEMS = (
        ("nav.overview", "overview"),
        ("nav.rules", "rules"),
        ("nav.connections", "connections"),
        ("nav.diagnostics", "diagnostics"),
        ("nav.settings", "settings"),
    )
    COMPACT_NAV_BELOW = 900  # window width at which the sidebar collapses to icons
    NAV_WIDTH, NAV_WIDTH_COMPACT = 216, 64

    def __init__(
        self,
        discovery_service: DiscoveryService,
        policy_repo: PolicyRepositoryPort,
        helper: PrivilegedHelper,
        theme_manager: ThemeManager,
        refresher: DiscoveryRefresher | None = None,
        app_icon: QIcon | None = None,
    ) -> None:
        super().__init__()
        self.discovery_service = discovery_service
        self.policy_repo = policy_repo
        self.helper = helper
        self.theme_manager = theme_manager
        self.refresher = refresher
        self.i18n = TranslationManager.instance()
        self._compact_nav: bool | None = None

        self.resize(1040, 700)
        self.setMinimumSize(QSize(480, 420))
        if app_icon:
            self.setWindowIcon(app_icon)

        self.overview_vm = OverviewViewModel(discovery_service, policy_repo)
        self.rules_vm = RulesViewModel(policy_repo)
        self.connections_vm = ConnectionsViewModel(discovery_service)
        self.diagnostics_vm = DiagnosticsViewModel(discovery_service, policy_repo)
        self.settings_vm = SettingsViewModel(theme_manager, self.rules_vm, helper)

        self.nav_buttons: dict[int, QPushButton] = {}
        self._setup_ui()
        self._connect_signals()
        self.tray_manager = TrayIconManager(
            icon=app_icon or QIcon(),
            on_toggle_window=self._toggle_visibility,
            on_open_rules=self._show_rules,
            on_quit=self._quit,
        )
        self.retranslate_ui()

    @property
    def pages(self) -> list[BasePage]:
        return [
            self.overview_view,
            self.rules_view,
            self.connections_view,
            self.diagnostics_view,
            self.settings_view,
        ]

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav_frame = QFrame()
        self.nav_frame.setObjectName("navBar")
        nav_layout = QVBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(10, 18, 10, 18)
        nav_layout.setSpacing(4)

        self.brand_label = QLabel("RoutePilot")
        self.brand_label.setObjectName("brandLabel")
        self.brand_label.setContentsMargins(10, 0, 10, 14)
        nav_layout.addWidget(self.brand_label)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (_key, _icon) in enumerate(self.NAV_ITEMS):
            btn = QPushButton()
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(btn, index)
            self.nav_buttons[index] = btn
            nav_layout.addWidget(btn)
        self.nav_buttons[0].setChecked(True)
        self.nav_group.idClicked.connect(self.switch_to_tab)
        nav_layout.addStretch()
        layout.addWidget(self.nav_frame)

        self.stack = QStackedWidget()
        self.overview_view = OverviewView(self.overview_vm, lambda: self.switch_to_tab(1))
        self.rules_view = RulesView(
            self.rules_vm, on_edit_rule=self._open_rule_editor, on_apply=self.helper.apply_policy
        )
        self.connections_view = ConnectionsView(self.connections_vm, on_refresh=self._refresh)
        self.diagnostics_view = DiagnosticsView(self.diagnostics_vm)
        self.settings_view = SettingsView(self.settings_vm)
        for page in self.pages:
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.net_status = QLabel()
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.setSizeGripEnabled(False)
            status_bar.addPermanentWidget(self.net_status)

    def _connect_signals(self) -> None:
        self.i18n.language_changed.connect(lambda _: self.retranslate_ui())
        self.rules_vm.policy_changed.connect(self.helper.apply_policy)
        self.rules_vm.policy_changed.connect(self.overview_vm.refresh)
        self.helper.busy_changed.connect(self._on_helper_busy)
        self.helper.finished.connect(self._on_helper_finished)
        self.helper.auth_cancelled.connect(
            lambda _cmd: self.show_status(self.i18n.t("status.auth_cancelled"), "error")
        )
        self.settings_vm.theme_changed.connect(lambda _: self.refresh_icons())
        if self.refresher:
            self.refresher.refreshing.connect(self._on_refreshing)

    def retranslate_ui(self) -> None:
        """Retranslates the window chrome and every page."""
        t = self.i18n.t
        self.setWindowTitle(t("app.title"))
        for index, (key, _icon) in enumerate(self.NAV_ITEMS):
            self.nav_buttons[index].setToolTip(t(key))
        self._apply_nav_mode(force=True)
        self.refresh_icons()
        for page in self.pages:
            page.retranslate_ui()

    def refresh_icons(self) -> None:
        """Re-renders icons in the current theme's colors (after a theme change)."""
        palette = self.theme_manager.palette()
        for index, (_key, icon) in enumerate(self.NAV_ITEMS):
            self.nav_buttons[index].setIcon(
                Icons.get(icon, palette["muted"], checked_color=palette["on_primary"])
            )
        self.rules_view.refresh_icons(self.theme_manager.palette())

    def switch_to_tab(self, index: int) -> None:
        """Switches current page and syncs nav button state."""
        self.stack.setCurrentIndex(index)
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)

    def show_status(self, message: str, state: str = "") -> None:
        status_bar = self.statusBar()
        if status_bar is None:
            return
        status_bar.setProperty("state", state)
        ThemeManager.repolish(status_bar)
        status_bar.showMessage(message, 0 if state == "error" else 8000)

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_nav_mode()

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802
        if self.refresher:
            self.refresher.stop()
        self.tray_manager.hide()
        super().closeEvent(event)

    def _apply_nav_mode(self, force: bool = False) -> None:
        compact = self.width() < self.COMPACT_NAV_BELOW
        if compact == self._compact_nav and not force:
            return
        self._compact_nav = compact
        self.nav_frame.setFixedWidth(self.NAV_WIDTH_COMPACT if compact else self.NAV_WIDTH)
        self.brand_label.setText("RP" if compact else "RoutePilot")
        self.brand_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignLeading
        )
        for index, (key, _icon) in enumerate(self.NAV_ITEMS):
            btn = self.nav_buttons[index]
            btn.setText("" if compact else f"  {self.i18n.t(key)}")
            btn.setProperty("compact", compact)
            ThemeManager.repolish(btn)

    def _open_rule_editor(self, rule: RoutingRule | None) -> None:
        dialog = RuleEditorDialog(
            existing_rule=rule, vpns=self.discovery_service.get_active_vpns(), parent=self
        )
        if dialog.exec() == RuleEditorDialog.DialogCode.Accepted:
            saved = dialog.get_rule()
            if saved:
                self.rules_vm.save_or_update_rule(saved)

    def _refresh(self) -> None:
        if self.refresher:
            self.refresher.refresh_now()

    def _on_refreshing(self, running: bool) -> None:
        t = self.i18n.t
        self.net_status.setText(
            t("status.scanning") if running else t("status.updated", time=f"{datetime.now():%H:%M}")
        )
        self.connections_view.set_refreshing(running)

    def _on_helper_busy(self, busy: bool) -> None:
        self.rules_view.set_applying(busy)
        if busy:
            self.show_status(self.i18n.t("status.applying"))

    def _on_helper_finished(self, command: str, success: bool, message: str) -> None:
        t = self.i18n.t
        if command == "reset":
            text = t("status.reset_done") if success else t("status.reset_failed", error=message)
        else:
            text = t("status.applied") if success else t("status.apply_failed", error=message)
        self.show_status(text, "success" if success else "error")
        if self.refresher:
            self.refresher.refresh_now()

    def _show_rules(self) -> None:
        self.show()
        self.switch_to_tab(1)

    def _quit(self) -> None:
        self.close()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
