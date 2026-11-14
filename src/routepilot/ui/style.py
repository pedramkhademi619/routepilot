"""Theme and styling manager for RoutePilot PyQt6 application."""

from PyQt6.QtWidgets import QApplication


class ThemeManager:
    """Manages application stylesheet and palette switching (Dark, Light, System)."""

    DARK_STYLESHEET = """
    QMainWindow, QWidget#centralWidget {
        background-color: #121418;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", sans-serif;
        font-size: 13px;
    }

    QFrame#navBar {
        background-color: #1A1D24;
        border-right: 1px solid #2D3748;
    }

    QPushButton#navButton {
        background-color: transparent;
        color: #A0AEC0;
        text-align: left;
        padding: 10px 16px;
        font-size: 13px;
        font-weight: 500;
        border-radius: 6px;
        border: none;
        margin: 2px 8px;
    }

    QPushButton#navButton:hover {
        background-color: #2D3748;
        color: #FFFFFF;
    }

    QPushButton#navButton:checked {
        background-color: #3182CE;
        color: #FFFFFF;
        font-weight: 600;
    }

    QFrame#card {
        background-color: #1A1D24;
        border: 1px solid #2D3748;
        border-radius: 8px;
        padding: 16px;
    }

    QLabel#titleLabel {
        font-size: 20px;
        font-weight: 700;
        color: #FFFFFF;
    }

    QLabel#subtitleLabel {
        font-size: 13px;
        color: #A0AEC0;
    }

    QLabel#cardTitle {
        font-size: 15px;
        font-weight: 600;
        color: #EDF2F7;
    }

    QLabel#badgeVpn {
        background-color: #2C5282;
        color: #BEE3F8;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    QLabel#badgeDirect {
        background-color: #22543D;
        color: #C6F6D5;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    QLabel#badgeOffline {
        background-color: #4A5568;
        color: #E2E8F0;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
    }

    QPushButton#primaryButton {
        background-color: #3182CE;
        color: #FFFFFF;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QPushButton#primaryButton:hover {
        background-color: #2B6CB0;
    }

    QPushButton#secondaryButton {
        background-color: #2D3748;
        color: #E2E8F0;
        border: 1px solid #4A5568;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QPushButton#secondaryButton:hover {
        background-color: #4A5568;
    }

    QPushButton#dangerButton {
        background-color: #9B2C2C;
        color: #FFF5F5;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QPushButton#dangerButton:hover {
        background-color: #822727;
    }

    QLineEdit, QComboBox, QSpinBox {
        background-color: #121418;
        color: #E2E8F0;
        border: 1px solid #4A5568;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid #3182CE;
    }

    QTableWidget {
        background-color: #1A1D24;
        alternate-background-color: #16181E;
        color: #E2E8F0;
        border: 1px solid #2D3748;
        border-radius: 6px;
        gridline-color: #242B35;
        selection-background-color: #2B6CB0;
        selection-color: #FFFFFF;
    }

    QTableWidget QPushButton {
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 500;
        border-radius: 4px;
    }

    QHeaderView::section {
        background-color: #121418;
        color: #A0AEC0;
        font-weight: 600;
        font-size: 12px;
        padding: 6px 10px;
        border: none;
        border-bottom: 1px solid #2D3748;
    }

    QScrollBar:vertical {
        background-color: #121418;
        width: 8px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background-color: #4A5568;
        border-radius: 4px;
        min-height: 20px;
    }
    """

    LIGHT_STYLESHEET = """
    QMainWindow, QWidget#centralWidget {
        background-color: #F7FAFC;
        color: #2D3748;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", sans-serif;
        font-size: 13px;
    }

    QFrame#navBar {
        background-color: #EDF2F7;
        border-right: 1px solid #E2E8F0;
    }

    QPushButton#navButton {
        background-color: transparent;
        color: #4A5568;
        text-align: left;
        padding: 10px 16px;
        font-size: 13px;
        font-weight: 500;
        border-radius: 6px;
        border: none;
        margin: 2px 8px;
    }

    QPushButton#navButton:hover {
        background-color: #E2E8F0;
        color: #1A202C;
    }

    QPushButton#navButton:checked {
        background-color: #3182CE;
        color: #FFFFFF;
        font-weight: 600;
    }

    QFrame#card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
    }

    QLabel#titleLabel {
        font-size: 20px;
        font-weight: 700;
        color: #1A202C;
    }

    QLabel#subtitleLabel {
        font-size: 13px;
        color: #718096;
    }

    QLabel#cardTitle {
        font-size: 15px;
        font-weight: 600;
        color: #2D3748;
    }

    QLabel#badgeVpn {
        background-color: #BEE3F8;
        color: #2B6CB0;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    QLabel#badgeDirect {
        background-color: #C6F6D5;
        color: #22543D;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    QLabel#badgeOffline {
        background-color: #EDF2F7;
        color: #718096;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
    }

    QPushButton#primaryButton {
        background-color: #3182CE;
        color: #FFFFFF;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QPushButton#primaryButton:hover {
        background-color: #2B6CB0;
    }

    QPushButton#secondaryButton {
        background-color: #EDF2F7;
        color: #2D3748;
        border: 1px solid #CBD5E0;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QPushButton#secondaryButton:hover {
        background-color: #E2E8F0;
    }

    QPushButton#dangerButton {
        background-color: #E53E3E;
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }

    QLineEdit, QComboBox, QSpinBox {
        background-color: #FFFFFF;
        color: #2D3748;
        border: 1px solid #CBD5E0;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }

    QTableWidget {
        background-color: #FFFFFF;
        alternate-background-color: #F8FAFC;
        color: #2D3748;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        gridline-color: #EDF2F7;
        selection-background-color: #3182CE;
        selection-color: #FFFFFF;
    }

    QTableWidget QPushButton {
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 500;
        border-radius: 4px;
    }

    QHeaderView::section {
        background-color: #F7FAFC;
        color: #718096;
        font-weight: 600;
        font-size: 12px;
        padding: 6px 10px;
        border: none;
        border-bottom: 1px solid #E2E8F0;
    }
    """

    @classmethod
    def apply_theme(cls, app: QApplication, theme_name: str = "dark") -> None:
        """Applies stylesheet to the QApplication."""
        if theme_name.lower() == "light":
            app.setStyleSheet(cls.LIGHT_STYLESHEET)
        else:
            app.setStyleSheet(cls.DARK_STYLESHEET)
