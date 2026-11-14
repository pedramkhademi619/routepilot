"""Settings View for application preferences, language selection, and emergency maintenance."""

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsView(QWidget):
    """View managing application preferences, language, appearance, and emergency cleanup."""

    def __init__(self, viewmodel: SettingsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.i18n = TranslationManager.instance()

        self._setup_ui()
        self.viewmodel.reset_completed.connect(self._on_reset_completed)
        self.viewmodel.language_changed.connect(self._on_language_changed)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout_container = QVBoxLayout(container)
        self.layout_container.setContentsMargins(24, 24, 24, 24)
        self.layout_container.setSpacing(20)

        # Header
        title_box = QVBoxLayout()
        self.title = QLabel("Settings & Maintenance")
        self.title.setObjectName("titleLabel")
        self.subtitle = QLabel(
            "Appearance preferences, language selection, and emergency system maintenance."
        )
        self.subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        self.layout_container.addLayout(title_box)

        # Language Card
        self.lang_card = QFrame()
        self.lang_card.setObjectName("card")
        lang_layout = QVBoxLayout(self.lang_card)
        self.lang_title = QLabel("Interface Language")
        self.lang_title.setObjectName("cardTitle")
        lang_layout.addWidget(self.lang_title)

        lang_row = QHBoxLayout()
        self.lang_label = QLabel("Language:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("فارسی (Persian)", "fa")

        # Select currently active language
        idx = self.lang_combo.findData(self.viewmodel.current_language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)

        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        self.layout_container.addWidget(self.lang_card)

        # Theme Card
        self.theme_card = QFrame()
        self.theme_card.setObjectName("card")
        theme_layout = QVBoxLayout(self.theme_card)
        self.theme_title = QLabel("Appearance Theme")
        self.theme_title.setObjectName("cardTitle")
        theme_layout.addWidget(self.theme_title)

        theme_row = QHBoxLayout()
        self.theme_label = QLabel("Color Scheme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme", "dark")
        self.theme_combo.addItem("Light Theme", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        theme_row.addWidget(self.theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        theme_layout.addLayout(theme_row)
        self.layout_container.addWidget(self.theme_card)

        # Emergency Reset Card
        self.reset_card = QFrame()
        self.reset_card.setObjectName("card")
        reset_layout = QVBoxLayout(self.reset_card)
        self.reset_title = QLabel("Emergency State Purge")
        self.reset_title.setObjectName("cardTitle")
        self.reset_desc = QLabel(
            "Purges all RoutePilot nftables tables, policy routing rules, and custom tables.\n"
            "Use this if network connectivity feels stalled or after an unexpected service crash."
        )
        self.reset_desc.setWordWrap(True)
        self.reset_desc.setStyleSheet("color: #A0AEC0;")

        btn_row = QHBoxLayout()
        self.reset_btn = QPushButton("Emergency Reset Kernel State")
        self.reset_btn.setObjectName("dangerButton")
        self.reset_btn.clicked.connect(self._on_emergency_reset_clicked)

        self.clear_rules_btn = QPushButton("Clear All Rules")
        self.clear_rules_btn.setObjectName("secondaryButton")
        self.clear_rules_btn.clicked.connect(self._on_clear_rules_clicked)

        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.clear_rules_btn)
        btn_row.addStretch()

        reset_layout.addWidget(self.reset_title)
        reset_layout.addWidget(self.reset_desc)
        reset_layout.addLayout(btn_row)
        self.layout_container.addWidget(self.reset_card)

        # About & License Card
        self.about_card = QFrame()
        self.about_card.setObjectName("card")
        about_layout = QVBoxLayout(self.about_card)
        self.about_title = QLabel("About RoutePilot")
        self.about_title.setObjectName("cardTitle")
        self.about_desc = QLabel(
            "RoutePilot v0.1.0\n"
            "Open-source Linux Desktop Utility for Selective VPN Bypass and Traffic Routing.\n"
            "Licensed under GNU General Public License v3.0 or later (GPL-3.0-or-later).\n"
            "https://github.com/routepilot/routepilot"
        )
        self.about_desc.setStyleSheet("color: #A0AEC0; line-height: 1.4;")
        about_layout.addWidget(self.about_title)
        about_layout.addWidget(self.about_desc)
        self.layout_container.addWidget(self.about_card)

        self.layout_container.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates all labels and controls in SettingsView."""
        t = self.i18n.tr
        self.title.setText(t("settings.title"))
        self.subtitle.setText(t("settings.subtitle"))

        # Language card
        self.lang_title.setText(t("settings.lang_card"))
        self.lang_label.setText(t("settings.lang_label"))

        # Theme card
        self.theme_title.setText(t("settings.theme_card"))
        self.theme_label.setText(t("settings.theme_label"))
        self.theme_combo.setItemText(0, t("settings.theme_dark"))
        self.theme_combo.setItemText(1, t("settings.theme_light"))

        # Purge card
        self.reset_title.setText(t("settings.purge_card"))
        self.reset_desc.setText(t("settings.purge_desc"))
        self.reset_btn.setText(t("settings.reset_btn"))
        self.clear_rules_btn.setText(t("settings.clear_btn"))

        # About card
        self.about_title.setText(t("settings.about_title"))
        self.about_desc.setText(t("settings.about_desc"))

    def _on_lang_combo_changed(self) -> None:
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.viewmodel.set_language(lang_code)

    def _on_language_changed(self, lang_code: str) -> None:
        # Update combo index if needed without triggering recursion
        self.lang_combo.blockSignals(True)
        idx = self.lang_combo.findData(lang_code)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.blockSignals(False)
        self.retranslate_ui()

    def _on_theme_changed(self) -> None:
        theme = self.theme_combo.currentData()
        self.viewmodel.set_theme(theme)

    def _on_emergency_reset_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirm Emergency Reset" if self.i18n.current_language == "en" else "تأیید بازنشانی اضطراری",
            "Are you sure you want to purge all RoutePilot kernel state and tables?"
            if self.i18n.current_language == "en"
            else "آیا مطمئن هستید که می‌خواهید تمام جداول و وضعیت هسته RoutePilot پاک شود؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.viewmodel.trigger_emergency_reset()

    def _on_clear_rules_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Confirm Clear Rules" if self.i18n.current_language == "en" else "تأیید حذف قوانین",
            "Are you sure you want to delete all configured routing rules?"
            if self.i18n.current_language == "en"
            else "آیا مطمئن هستید که می‌خواهید تمام قوانین حذف شوند؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.viewmodel.clear_all_rules()

    def _on_reset_completed(self, message: str) -> None:
        QMessageBox.information(self, "RoutePilot", message)
