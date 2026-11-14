"""Settings View for application preferences and emergency maintenance."""

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from routepilot.ui.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsView(QWidget):
    """View managing application preferences, appearance, and emergency cleanup."""

    def __init__(self, viewmodel: SettingsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel

        self._setup_ui()
        self.viewmodel.reset_completed.connect(self._on_reset_completed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        title_box = QVBoxLayout()
        title = QLabel("Settings & Maintenance")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Appearance preferences, emergency recovery, and system maintenance.")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Theme Card
        theme_card = QFrame()
        theme_card.setObjectName("card")
        theme_layout = QVBoxLayout(theme_card)
        theme_title = QLabel("Appearance Theme")
        theme_title.setObjectName("cardTitle")
        theme_layout.addWidget(theme_title)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Color Scheme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme", "dark")
        self.theme_combo.addItem("Light Theme", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        theme_layout.addLayout(theme_row)
        layout.addWidget(theme_card)

        # Emergency Reset Card
        reset_card = QFrame()
        reset_card.setObjectName("card")
        reset_layout = QVBoxLayout(reset_card)
        reset_title = QLabel("Emergency State Purge")
        reset_title.setObjectName("cardTitle")
        reset_desc = QLabel(
            "Purges all RoutePilot nftables tables, policy routing rules, and custom tables.\n"
            "Use this if network connectivity feels stalled or after an unexpected service crash."
        )
        reset_desc.setWordWrap(True)
        reset_desc.setStyleSheet("color: #A0AEC0;")

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Emergency Reset Kernel State")
        reset_btn.setObjectName("dangerButton")
        reset_btn.clicked.connect(self._on_emergency_reset_clicked)

        clear_rules_btn = QPushButton("Clear All Rules")
        clear_rules_btn.setObjectName("secondaryButton")
        clear_rules_btn.clicked.connect(self._on_clear_rules_clicked)

        btn_row.addWidget(reset_btn)
        btn_row.addWidget(clear_rules_btn)
        btn_row.addStretch()

        reset_layout.addWidget(reset_title)
        reset_layout.addWidget(reset_desc)
        reset_layout.addLayout(btn_row)
        layout.addWidget(reset_card)

        # About & License Card
        about_card = QFrame()
        about_card.setObjectName("card")
        about_layout = QVBoxLayout(about_card)
        about_title = QLabel("About RoutePilot")
        about_title.setObjectName("cardTitle")
        about_desc = QLabel(
            "RoutePilot v0.1.0\n"
            "Open-source Linux Desktop Utility for Selective VPN Bypass and Traffic Routing.\n"
            "Licensed under GNU General Public License v3.0 or later (GPL-3.0-or-later).\n"
            "https://github.com/routepilot/routepilot"
        )
        about_desc.setStyleSheet("color: #A0AEC0; line-height: 1.4;")
        about_layout.addWidget(about_title)
        about_layout.addWidget(about_desc)
        layout.addWidget(about_card)

        layout.addStretch()

    def _on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self.viewmodel.set_theme(theme)

    def _on_emergency_reset_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirm Emergency Reset",
            "Are you sure you want to purge all RoutePilot kernel state and tables?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.viewmodel.trigger_emergency_reset()

    def _on_clear_rules_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirm Clear Rules",
            "Are you sure you want to delete all configured routing rules?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.viewmodel.clear_all_rules()

    def _on_reset_completed(self, message: str) -> None:
        QMessageBox.information(self, "RoutePilot Maintenance", message)
