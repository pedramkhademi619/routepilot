"""System tray integration manager with fallback for non-tray desktop environments."""

import logging
from collections.abc import Callable

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from routepilot.ui.translation_manager import TranslationManager

logger = logging.getLogger(__name__)


class TrayIconManager(QObject):
    """Manages the tray icon and its menu; silently disabled where no tray exists."""

    def __init__(
        self,
        icon: QIcon,
        on_toggle_window: Callable[[], None],
        on_open_rules: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__()
        self.i18n = TranslationManager.instance()
        self.on_toggle_window = on_toggle_window
        self.tray_icon: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray is not available on this desktop environment.")
            return

        self.menu = QMenu()
        self.show_action = QAction(self.menu)
        self.show_action.triggered.connect(on_toggle_window)
        self.rules_action = QAction(self.menu)
        self.rules_action.triggered.connect(on_open_rules)
        self.quit_action = QAction(self.menu)
        self.quit_action.triggered.connect(on_quit)
        self.menu.addAction(self.show_action)
        self.menu.addAction(self.rules_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.i18n.language_changed.connect(lambda _: self.retranslate_ui())
        self.retranslate_ui()
        self.tray_icon.show()

    def retranslate_ui(self) -> None:
        if self.tray_icon is None:
            return
        t = self.i18n.t
        self.tray_icon.setToolTip(t("tray.tooltip"))
        self.show_action.setText(t("tray.show"))
        self.rules_action.setText(t("tray.rules"))
        self.quit_action.setText(t("tray.quit"))

    def hide(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.on_toggle_window()
