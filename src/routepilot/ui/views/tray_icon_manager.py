"""System tray integration manager with fallback for non-tray desktop environments."""

import logging
from collections.abc import Callable

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

logger = logging.getLogger(__name__)


class TrayIconManager(QObject):
    """Manages system tray icon, menu actions, and desktop availability fallbacks."""

    def __init__(
        self,
        on_toggle_window: Callable[[], None],
        on_open_rules: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_toggle_window = on_toggle_window
        self.on_open_rules = on_open_rules
        self.on_quit = on_quit

        self.tray_icon: QSystemTrayIcon | None = None
        self._init_tray()

    def _init_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray is not supported or unavailable on this desktop environment.")
            return

        icon = self._create_icon()
        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setToolTip("RoutePilot — Traffic Routing & VPN Bypass")

        menu = QMenu()
        show_action = QAction("Show RoutePilot", menu)
        show_action.triggered.connect(self.on_toggle_window)
        menu.addAction(show_action)

        rules_action = QAction("Traffic Rules...", menu)
        rules_action.triggered.connect(self.on_open_rules)
        menu.addAction(rules_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.on_quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_icon(self) -> QIcon:
        # Generates a clean 32x32 circular emblem icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#3182CE"))
        painter.setPen(QColor("#2B6CB0"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(14)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x0084, "RP")  # AlignCenter
        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.on_toggle_window()
