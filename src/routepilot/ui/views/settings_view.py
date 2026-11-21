"""Settings View for language, appearance and emergency maintenance."""

from PyQt6.QtWidgets import QComboBox, QFormLayout, QLabel, QMessageBox, QPushButton, QWidget

from routepilot import __version__
from routepilot.ui.style import ThemeManager
from routepilot.ui.viewmodels.settings_viewmodel import SettingsViewModel
from routepilot.ui.views.base_page import BasePage
from routepilot.ui.widgets.card import Card
from routepilot.ui.widgets.flow_layout import FlowLayout

PROJECT_URL = "https://github.com/pedramkhademi619/routepilot"


class SettingsView(BasePage):
    """Application preferences, language, appearance, and emergency cleanup."""

    def __init__(self, viewmodel: SettingsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel

        self.prefs_card = Card()
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setHorizontalSpacing(16)
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        for code, native_name in viewmodel.languages.items():
            self.lang_combo.addItem(native_name, code)
        self._select(self.lang_combo, viewmodel.current_language)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)
        self.theme_label = QLabel()
        self.theme_combo = QComboBox()
        for theme in ThemeManager.THEMES:
            self.theme_combo.addItem(theme, theme)
        self._select(self.theme_combo, viewmodel.current_theme)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(self.lang_label, self.lang_combo)
        form.addRow(self.theme_label, self.theme_combo)
        self.prefs_card.body.addLayout(form)
        self.content.addWidget(self.prefs_card)

        self.reset_card = Card()
        self.reset_desc = QLabel()
        self.reset_desc.setObjectName("mutedLabel")
        self.reset_desc.setWordWrap(True)
        self.reset_card.body.addWidget(self.reset_desc)
        buttons_host = QWidget()
        buttons = FlowLayout(buttons_host)
        self.reset_btn = QPushButton()
        self.reset_btn.setObjectName("dangerButton")
        self.reset_btn.clicked.connect(self._on_emergency_reset_clicked)
        self.clear_rules_btn = QPushButton()
        self.clear_rules_btn.setObjectName("secondaryButton")
        self.clear_rules_btn.clicked.connect(self._on_clear_rules_clicked)
        buttons.addWidget(self.reset_btn)
        buttons.addWidget(self.clear_rules_btn)
        self.reset_card.body.addWidget(buttons_host)
        self.content.addWidget(self.reset_card)

        self.about_card = Card()
        self.about_desc = QLabel()
        self.about_desc.setObjectName("mutedLabel")
        self.about_desc.setWordWrap(True)
        self.about_link = QLabel()
        self.about_link.setObjectName("link")
        self.about_link.setOpenExternalLinks(True)
        self.about_link.setWordWrap(True)
        self.about_card.body.addWidget(self.about_desc)
        self.about_card.body.addWidget(self.about_link)
        self.content.addWidget(self.about_card)
        self.content.addStretch()

        self.viewmodel.language_changed.connect(self._on_language_changed)

    def retranslate_ui(self) -> None:
        t = self.i18n.t
        self.header.set_text(t("settings.title"), t("settings.subtitle"))
        self.prefs_card.set_title(t("settings.prefs_card"))
        self.lang_label.setText(t("settings.lang_label"))
        self.theme_label.setText(t("settings.theme_label"))
        for index in range(self.theme_combo.count()):
            self.theme_combo.setItemText(
                index, t(f"settings.theme_{self.theme_combo.itemData(index)}")
            )
        self.reset_card.set_title(t("settings.maintenance_card"))
        self.reset_desc.setText(t("settings.maintenance_desc"))
        self.reset_btn.setText(t("settings.reset_btn"))
        self.clear_rules_btn.setText(t("settings.clear_btn"))
        self.about_card.set_title(t("settings.about_title"))
        self.about_desc.setText(t("settings.about_desc", version=__version__))
        self.about_link.setText(f'<a href="{PROJECT_URL}">{t("settings.about_link")}</a>')

    def _on_lang_combo_changed(self) -> None:
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self.viewmodel.set_language(lang_code)

    def _on_language_changed(self, lang_code: str) -> None:
        self.lang_combo.blockSignals(True)
        self._select(self.lang_combo, lang_code)
        self.lang_combo.blockSignals(False)

    def _on_theme_changed(self) -> None:
        self.viewmodel.set_theme(self.theme_combo.currentData())

    def _confirm(self, title_key: str, body_key: str) -> bool:
        t = self.i18n.t
        answer = QMessageBox.question(
            self,
            t(title_key),
            t(body_key),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _on_emergency_reset_clicked(self) -> None:
        if self._confirm("settings.confirm_reset_title", "settings.confirm_reset_body"):
            self.viewmodel.trigger_emergency_reset()

    def _on_clear_rules_clicked(self) -> None:
        if self._confirm("settings.confirm_clear_title", "settings.confirm_clear_body"):
            self.viewmodel.clear_all_rules()

    @staticmethod
    def _select(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
