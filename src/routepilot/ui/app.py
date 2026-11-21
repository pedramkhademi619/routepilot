"""Desktop entry point: composition root wiring adapters, services and the Qt GUI."""

import argparse
import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from routepilot import __version__
from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter
from routepilot.infrastructure.adapters.nm_discovery_adapter import NetworkManagerDiscoveryAdapter
from routepilot.ui.controllers.discovery_refresher import DiscoveryRefresher
from routepilot.ui.controllers.privileged_helper import PrivilegedHelper
from routepilot.ui.style import ThemeManager
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.views.main_window import MainWindow

ICON_PATH = Path(__file__).with_name("resources") / "routepilot.svg"


class RoutePilotApp:
    """Owns the Qt application and the object graph of the desktop UI."""

    def __init__(self, use_mock: bool = False) -> None:
        existing = QApplication.instance()
        self.app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
        self.app.setApplicationName("RoutePilot")
        self.app.setApplicationVersion(__version__)
        self.app.setDesktopFileName("routepilot")
        icon = QIcon(str(ICON_PATH))
        self.app.setWindowIcon(icon)

        discovery: NetworkDiscoveryPort = (
            MockDiscoveryAdapter() if use_mock else NetworkManagerDiscoveryAdapter()
        )
        self.policy_repo = JsonPolicyRepositoryAdapter()
        self.discovery_service = DiscoveryService(discovery)
        self.refresher = DiscoveryRefresher(self.discovery_service)
        self.helper = PrivilegedHelper(self.policy_repo.file_path)

        i18n = TranslationManager.instance()
        i18n.apply_layout_direction()
        self.theme_manager = ThemeManager()
        self.theme_manager.apply(self.app)
        hints = self.app.styleHints()
        if hints is not None:
            hints.colorSchemeChanged.connect(self._on_system_scheme_changed)

        self.main_window = MainWindow(
            discovery_service=self.discovery_service,
            policy_repo=self.policy_repo,
            helper=self.helper,
            theme_manager=self.theme_manager,
            refresher=self.refresher,
            app_icon=icon,
        )

    def run(self) -> int:
        self.main_window.show()
        self.refresher.start()
        return int(self.app.exec())

    def _on_system_scheme_changed(self) -> None:
        if self.theme_manager.theme == "system":
            self.theme_manager.apply(self.app)
            self.main_window.refresh_icons()


def main() -> None:
    parser = argparse.ArgumentParser(prog="routepilot-gui", description="RoutePilot desktop app")
    parser.add_argument("--mock", action="store_true", help="Use a simulated network (demo mode)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args, qt_args = parser.parse_known_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    sys.argv = [sys.argv[0], *qt_args]
    sys.exit(RoutePilotApp(use_mock=args.mock).run())


if __name__ == "__main__":
    main()
