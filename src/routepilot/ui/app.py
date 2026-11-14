"""Application entry point wiring ports, adapters, and Qt GUI."""

import asyncio
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.infrastructure.adapters.nftables_firewall_adapter import NftablesFirewallAdapter
from routepilot.infrastructure.adapters.nm_discovery_adapter import NetworkManagerDiscoveryAdapter
from routepilot.infrastructure.adapters.pyroute2_routing_adapter import Pyroute2RoutingAdapter
from routepilot.ui.style import ThemeManager
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.views.main_window import MainWindow


class RoutePilotApp:
    """Dependency injection orchestrator and Qt application lifecycle manager."""

    def __init__(self, use_mock: bool = False) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("RoutePilot")
        self.app.setOrganizationName("RoutePilot")

        # Hexagonal Wiring: Adapters
        self.discovery_adapter: NetworkDiscoveryPort = (
            MockDiscoveryAdapter() if use_mock else NetworkManagerDiscoveryAdapter()
        )
        self.policy_repo = JsonPolicyRepositoryAdapter()
        self.routing_adapter = Pyroute2RoutingAdapter()
        self.firewall_adapter = NftablesFirewallAdapter()

        # Application Services
        self.discovery_service = DiscoveryService(self.discovery_adapter)
        self.reconciliation_service = ReconciliationService(
            self.routing_adapter, self.firewall_adapter
        )

        # Style & Localization
        ThemeManager.apply_theme(self.app, "dark")
        i18n = TranslationManager.instance()
        if i18n.current_language == "fa":
            self.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.main_window = MainWindow(
            discovery_service=self.discovery_service,
            policy_repo=self.policy_repo,
            reconciliation_service=self.reconciliation_service,
            on_theme_changed=self._on_theme_changed,
        )

    def run(self) -> int:
        """Initializes asynchronous discovery and starts the Qt main event loop."""
        self.main_window.show()

        # Run initial discovery in event loop or synchronously
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.discovery_service.refresh())
        except Exception:
            pass

        return self.app.exec()

    def _on_theme_changed(self, theme_name: str) -> None:
        ThemeManager.apply_theme(self.app, theme_name)


def main() -> None:
    use_mock = "--mock" in sys.argv
    app = RoutePilotApp(use_mock=use_mock)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
