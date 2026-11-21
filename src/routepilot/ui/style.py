"""Theme and styling manager for RoutePilot PyQt6 application."""

import atexit
import shutil
import tempfile
from pathlib import Path
from string import Template

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPalette
from PyQt6.QtWidgets import QApplication, QWidget

from routepilot.ui.settings_store import UiSettingsStore

_PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0F1115",
        "surface": "#171A21",
        "surface_alt": "#1E222B",
        "border": "#2A303C",
        "text": "#E6E9EF",
        "muted": "#9AA3B2",
        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "on_primary": "#FFFFFF",
        "success_bg": "#12382A",
        "success_fg": "#7EE2B8",
        "info_bg": "#1E3A5F",
        "info_fg": "#A9CCFF",
        "neutral_bg": "#2A303C",
        "neutral_fg": "#C9D1DD",
        "danger": "#DC2626",
        "danger_hover": "#B91C1C",
        "danger_fg": "#FCA5A5",
        "warning_fg": "#FBBF24",
        "input_bg": "#12151B",
        "selection": "#1D4ED8",
        "nav_bg": "#13161C",
        "hover": "#232833",
    },
    "light": {
        "bg": "#F5F7FA",
        "surface": "#FFFFFF",
        "surface_alt": "#F0F3F7",
        "border": "#DDE3EA",
        "text": "#1A202C",
        "muted": "#5B6573",
        "primary": "#2563EB",
        "primary_hover": "#1D4ED8",
        "on_primary": "#FFFFFF",
        "success_bg": "#DCFCE7",
        "success_fg": "#166534",
        "info_bg": "#DBEAFE",
        "info_fg": "#1E40AF",
        "neutral_bg": "#EEF1F5",
        "neutral_fg": "#475569",
        "danger": "#DC2626",
        "danger_hover": "#B91C1C",
        "danger_fg": "#B91C1C",
        "warning_fg": "#B45309",
        "input_bg": "#FFFFFF",
        "selection": "#2563EB",
        "nav_bg": "#EEF1F6",
        "hover": "#E6EBF1",
    },
}

_ASSETS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5" stroke="#FFFFFF" stroke-width="3"/>',
    "chevron_down": '<path d="m6 9 6 6 6-6" stroke="{muted}" stroke-width="2.5"/>',
    "chevron_up": '<path d="m6 15 6-6 6 6" stroke="{muted}" stroke-width="2.5"/>',
}

_STYLESHEET = Template("""
QMainWindow, QDialog, QWidget#centralWidget, QWidget#page, QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: $bg;
    color: $text;
}
QWidget { font-size: 13px; color: $text; }
QToolTip { background-color: $surface_alt; color: $text; border: 1px solid $border; padding: 4px 6px; }

QFrame#navBar { background-color: $nav_bg; border: none; border-$nav_edge: 1px solid $border; }
QLabel#brandLabel { font-size: 16px; font-weight: 700; color: $text; }
QPushButton#navButton {
    background-color: transparent; color: $muted; text-align: $start;
    padding: 9px 12px; font-weight: 500; border-radius: 8px; border: none;
}
QPushButton#navButton[compact="true"] { text-align: center; padding: 9px 0; }
QPushButton#navButton:hover { background-color: $hover; color: $text; }
QPushButton#navButton:checked { background-color: $primary; color: $on_primary; font-weight: 600; }

QFrame#card { background-color: $surface; border: 1px solid $border; border-radius: 10px; }
QLabel#titleLabel { font-size: 21px; font-weight: 700; color: $text; }
QLabel#subtitleLabel, QLabel#mutedLabel { color: $muted; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; color: $text; }
QLabel#heroLabel { font-size: 17px; font-weight: 600; color: $text; }
QLabel#statValue { font-size: 22px; font-weight: 700; color: $text; }
QLabel#statLabel { color: $muted; font-size: 12px; }
QLabel#fieldLabel { color: $muted; }
QLabel#errorLabel { color: $danger_fg; font-weight: 500; }
QLabel#previewLabel { color: $info_fg; }
QLabel#resultTitle { font-size: 15px; font-weight: 700; color: $text; }
QLabel#resultTitle[state="blocked"] { color: $danger_fg; }
QLabel#resultTitle[state="routed"] { color: $success_fg; }
QLabel#emptyTitle { font-size: 16px; font-weight: 600; color: $text; }
QLabel#link { color: $primary; }

QLabel#badgeVpn, QLabel#badgeDirect, QLabel#badgeOffline {
    padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;
}
QLabel#badgeVpn { background-color: $info_bg; color: $info_fg; }
QLabel#badgeDirect { background-color: $success_bg; color: $success_fg; }
QLabel#badgeOffline { background-color: $neutral_bg; color: $neutral_fg; }

QPushButton { min-height: 20px; }
QPushButton#primaryButton, QPushButton#secondaryButton, QPushButton#dangerButton {
    border-radius: 8px; padding: 8px 14px; font-weight: 600;
}
QPushButton#primaryButton { background-color: $primary; color: $on_primary; border: none; }
QPushButton#primaryButton:hover { background-color: $primary_hover; }
QPushButton#primaryButton:disabled { background-color: $neutral_bg; color: $muted; }
QPushButton#secondaryButton { background-color: $surface_alt; color: $text; border: 1px solid $border; }
QPushButton#secondaryButton:hover { background-color: $hover; }
QPushButton#dangerButton { background-color: $danger; color: #FFFFFF; border: none; }
QPushButton#dangerButton:hover { background-color: $danger_hover; }

QToolButton#iconButton { background: transparent; border: none; border-radius: 6px; padding: 4px; }
QToolButton#iconButton:hover { background-color: $hover; }

QLineEdit, QComboBox, QSpinBox {
    background-color: $input_bg; color: $text; border: 1px solid $border;
    border-radius: 8px; padding: 7px 10px; selection-background-color: $selection;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid $primary; }
QComboBox::drop-down { border: none; width: 26px; subcontrol-position: center $end; }
QComboBox::down-arrow { image: url("$chevron_down"); width: 12px; height: 12px; }
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border; width: 22px; border: none; background: transparent;
}
QSpinBox::up-button { subcontrol-position: top right; }
QSpinBox::down-button { subcontrol-position: bottom right; }
QSpinBox::up-arrow { image: url("$chevron_up"); width: 10px; height: 10px; }
QSpinBox::down-arrow { image: url("$chevron_down"); width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background-color: $surface; color: $text; border: 1px solid $border;
    selection-background-color: $selection; selection-color: #FFFFFF;
}

QTableWidget {
    background-color: $surface; alternate-background-color: $surface_alt; color: $text;
    border: 1px solid $border; border-radius: 10px; gridline-color: transparent;
    selection-background-color: $selection; selection-color: #FFFFFF;
}
QTableWidget::item { padding: 0 8px; }
QHeaderView::section {
    background-color: $surface; color: $muted; font-weight: 600; font-size: 12px;
    padding: 8px; border: none; border-bottom: 1px solid $border;
}
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 5px;
    border: 1.5px solid $muted; background-color: $input_bg;
}
QCheckBox::indicator:hover { border-color: $primary; }
QCheckBox::indicator:checked { background-color: $primary; border-color: $primary; image: url("$check"); }

QStatusBar { background-color: $nav_bg; color: $muted; border-top: 1px solid $border; }
QStatusBar QLabel { color: $muted; padding: 0 8px; }
QStatusBar[state="error"] { color: $danger_fg; }
QStatusBar[state="success"] { color: $success_fg; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background-color: $border; border-radius: 4px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background-color: $muted; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""")


class ThemeManager:
    """Generates the application stylesheet from palette tokens (dark, light or system)."""

    THEMES = ("system", "dark", "light")

    def __init__(self, store: UiSettingsStore | None = None) -> None:
        self._store = store or UiSettingsStore()
        self._asset_dir = Path(tempfile.mkdtemp(prefix="routepilot-theme-"))
        atexit.register(shutil.rmtree, self._asset_dir, ignore_errors=True)
        theme = self._store.get("theme", "system")
        self.theme = theme if theme in self.THEMES else "system"

    @property
    def effective_theme(self) -> str:
        """Resolves "system" to the desktop's current light/dark preference."""
        if self.theme != "system":
            return self.theme
        app = QGuiApplication.instance()
        hints = app.styleHints() if isinstance(app, QGuiApplication) else None
        if hints is not None and hints.colorScheme() == Qt.ColorScheme.Light:
            return "light"
        return "dark"

    def palette(self) -> dict[str, str]:
        return _PALETTES[self.effective_theme]

    def set_theme(self, theme: str, app: QApplication) -> None:
        self.theme = theme if theme in self.THEMES else "system"
        self._store.set("theme", self.theme)
        self.apply(app)

    def apply(self, app: QApplication) -> None:
        """(Re)applies style, palette and stylesheet; call after a theme or direction change."""
        colors = self.palette()
        rtl = app.layoutDirection() == Qt.LayoutDirection.RightToLeft
        app.setStyle("Fusion")  # consistent rendering of palette and QSS on every desktop
        app.setPalette(self._qpalette(colors))
        app.setStyleSheet(
            _STYLESHEET.substitute(
                colors,
                **self._write_assets(colors),
                start="right" if rtl else "left",
                end="left" if rtl else "right",
                nav_edge="left" if rtl else "right",
            )
        )

    def _write_assets(self, colors: dict[str, str]) -> dict[str, str]:
        """Writes theme-colored SVG glyphs that QSS ``image:`` properties can reference."""
        urls = {}
        for name, body in _ASSETS.items():
            path = self._asset_dir / f"{name}-{self.effective_theme}.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
                'stroke-linecap="round" stroke-linejoin="round">'
                f"{body.format(**colors)}</svg>",
                encoding="utf-8",
            )
            urls[name] = path.as_posix()
        return urls

    @staticmethod
    def _qpalette(colors: dict[str, str]) -> QPalette:
        """Native widgets (message boxes, file dialogs, links) follow the theme too."""
        role = QPalette.ColorRole
        palette = QPalette()
        for roles, key in (
            ((role.Window, role.Button), "bg"),
            ((role.Base, role.ToolTipBase), "surface"),
            ((role.AlternateBase,), "surface_alt"),
            ((role.WindowText, role.Text, role.ButtonText, role.ToolTipText), "text"),
            ((role.PlaceholderText,), "muted"),
            ((role.Highlight,), "selection"),
            ((role.Link, role.LinkVisited), "primary"),
        ):
            for color_role in roles:
                palette.setColor(color_role, QColor(colors[key]))
        palette.setColor(role.HighlightedText, QColor("#FFFFFF"))
        for color_role in (role.WindowText, role.Text, role.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(colors["muted"]))
        return palette

    @staticmethod
    def repolish(widget: QWidget) -> None:
        """Re-evaluates stylesheet selectors after a dynamic property changed."""
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
