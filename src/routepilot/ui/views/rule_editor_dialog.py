"""Guided Rule Editor Dialog with real-time validation and plain-language summary."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.rule_editor_viewmodel import RuleEditorViewModel


class RuleEditorDialog(QDialog):
    """Guided modal dialog for creating and editing RoutePilot policy rules."""

    def __init__(
        self, existing_rule: RoutingRule | None = None, parent: QDialog | None = None
    ) -> None:
        super().__init__(parent)
        self.viewmodel = RuleEditorViewModel(existing_rule)
        self.i18n = TranslationManager.instance()
        is_fa = self.i18n.current_language == "fa"

        if existing_rule:
            self.setWindowTitle(
                "ویرایش قانون ترافیک — RoutePilot" if is_fa else "Edit Rule — RoutePilot"
            )
        else:
            self.setWindowTitle(
                "قانون ترافیک جدید — RoutePilot" if is_fa else "New Rule — RoutePilot"
            )

        self.setMinimumWidth(580)
        self._saved_rule: RoutingRule | None = None

        self._setup_ui()
        self._connect_signals()
        self._on_input_changed()

    def get_rule(self) -> RoutingRule | None:
        return self._saved_rule

    def _setup_ui(self) -> None:
        t = self.i18n.tr
        is_fa = self.i18n.current_language == "fa"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header
        header = QLabel(t("editor.title_new") if not self.viewmodel._existing_rule else t("editor.title_edit"))
        header.setObjectName("titleLabel")
        layout.addWidget(header)

        # Form layout
        form = QFormLayout()
        form.setSpacing(12)

        # 1. Name
        self.name_input = QLineEdit(self.viewmodel.name)
        self.name_input.setPlaceholderText(
            "مثلاً بای‌پس بانک سامان یا soft98" if is_fa else "e.g. Bypass Local Banking"
        )
        form.addRow(t("editor.name"), self.name_input)

        # 2. Selector Type
        self.selector_combo = QComboBox()
        if is_fa:
            self.selector_combo.addItem("دامنه تکی (single domain)", SelectorType.DOMAIN)
            self.selector_combo.addItem(
                "دامنه و کلیه زیردامنه‌ها (*.example.com)", SelectorType.DOMAIN_AND_SUBDOMAINS
            )
            self.selector_combo.addItem("آدرس IP اختصاصی", SelectorType.IP_ADDRESS)
            self.selector_combo.addItem("ساب‌نت / رنج آی‌پی (CIDR)", SelectorType.CIDR)
            self.selector_combo.addItem("برنامه کاربردی (Cgroup Scope)", SelectorType.APPLICATION)
        else:
            self.selector_combo.addItem("Domain name (single)", SelectorType.DOMAIN)
            self.selector_combo.addItem(
                "Domain and all subdomains (*.example.com)", SelectorType.DOMAIN_AND_SUBDOMAINS
            )
            self.selector_combo.addItem("IP Address", SelectorType.IP_ADDRESS)
            self.selector_combo.addItem("CIDR Subnet (e.g. 192.168.1.0/24)", SelectorType.CIDR)
            self.selector_combo.addItem("Application Scope (ID)", SelectorType.APPLICATION)
        self._select_combo_data(self.selector_combo, self.viewmodel.selector_type)
        form.addRow(t("editor.target_type"), self.selector_combo)

        # 3. Selector Value
        self.value_input = QLineEdit(self.viewmodel.selector_value)
        self.value_input.setPlaceholderText("e.g. examplebank.ir or 198.51.100.0/24")
        form.addRow(t("editor.target_value"), self.value_input)

        # 4. Action
        self.action_combo = QComboBox()
        if is_fa:
            self.action_combo.addItem("عبور از اینترنت مستقیم (بای‌پس VPN)", ActionType.USE_DIRECT)
            self.action_combo.addItem("هدایت اختصاصی از VPN", ActionType.USE_SELECTED_VPN)
            self.action_combo.addItem("مسدودسازی ترافیک (بلاک)", ActionType.BLOCK)
            self.action_combo.addItem("پیروی از مسیریابی پیش‌فرض سیستم", ActionType.FOLLOW_SYSTEM)
        else:
            self.action_combo.addItem("Use Direct Internet (Bypass VPN)", ActionType.USE_DIRECT)
            self.action_combo.addItem("Exclusively Use VPN", ActionType.USE_SELECTED_VPN)
            self.action_combo.addItem("Block Traffic (Drop)", ActionType.BLOCK)
            self.action_combo.addItem("Follow System Routing", ActionType.FOLLOW_SYSTEM)
        self._select_combo_data(self.action_combo, self.viewmodel.action_type)
        form.addRow(t("editor.action"), self.action_combo)

        # 5. Priority
        self.prio_spin = QSpinBox()
        self.prio_spin.setRange(1, 9999)
        self.prio_spin.setValue(self.viewmodel.priority)
        form.addRow(t("editor.priority"), self.prio_spin)

        # 6. Condition
        self.condition_combo = QComboBox()
        if is_fa:
            self.condition_combo.addItem("همیشه فعال", ConditionType.ALWAYS)
            self.condition_combo.addItem("هنگام فعال بودن هرگونه VPN", ConditionType.ANY_VPN_ACTIVE)
            self.condition_combo.addItem(
                "هنگام فعال بودن VPN خاص", ConditionType.SPECIFIC_VPN_ACTIVE
            )
        else:
            self.condition_combo.addItem("Always Active", ConditionType.ALWAYS)
            self.condition_combo.addItem("Whenever Any VPN is Active", ConditionType.ANY_VPN_ACTIVE)
            self.condition_combo.addItem(
                "When Specific VPN is Active", ConditionType.SPECIFIC_VPN_ACTIVE
            )
        self._select_combo_data(self.condition_combo, self.viewmodel.condition_type)
        form.addRow(t("editor.condition"), self.condition_combo)

        # 7. Fallback Policy
        self.fallback_combo = QComboBox()
        if is_fa:
            self.fallback_combo.addItem("مسدودسازی در صورت قطعی (Fail-Closed)", FailureBehavior.BLOCK)
            self.fallback_combo.addItem(
                "استفاده از اینترنت پیش‌فرض سیستم (Fail-Open)", FailureBehavior.FOLLOW_SYSTEM
            )
        else:
            self.fallback_combo.addItem("Block Traffic (Fail-Closed, Safest)", FailureBehavior.BLOCK)
            self.fallback_combo.addItem(
                "Follow Default Routing (Fail-Open)", FailureBehavior.FOLLOW_SYSTEM
            )
        self._select_combo_data(self.fallback_combo, self.viewmodel.failure_behavior)
        form.addRow(t("editor.failure"), self.fallback_combo)

        layout.addLayout(form)

        # Live plain-language preview
        preview_box = QVBoxLayout()
        preview_title = QLabel(t("editor.explanation"))
        preview_title.setObjectName("cardTitle")
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #63B3ED; font-style: italic; padding: 6px 0;")
        preview_box.addWidget(preview_title)
        preview_box.addWidget(self.preview_label)
        layout.addLayout(preview_box)

        # Validation status message
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FC8181; font-weight: 500;")
        layout.addWidget(self.error_label)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton(t("editor.cancel"))
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.save_btn = QPushButton(t("editor.save"))
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._on_save_clicked)
        btn_box.addWidget(self.save_btn)

        layout.addLayout(btn_box)

    def _connect_signals(self) -> None:
        self.name_input.textChanged.connect(self._on_input_changed)
        self.value_input.textChanged.connect(self._on_input_changed)
        self.selector_combo.currentIndexChanged.connect(self._on_input_changed)
        self.action_combo.currentIndexChanged.connect(self._on_input_changed)
        self.condition_combo.currentIndexChanged.connect(self._on_input_changed)
        self.fallback_combo.currentIndexChanged.connect(self._on_input_changed)
        self.prio_spin.valueChanged.connect(self._on_input_changed)

        self.viewmodel.validation_changed.connect(self._on_validation_changed)
        self.viewmodel.preview_changed.connect(self.preview_label.setText)

    def _on_input_changed(self) -> None:
        sel_type = self.selector_combo.currentData()
        action_type = self.action_combo.currentData()
        cond_type = self.condition_combo.currentData()
        fail_type = self.fallback_combo.currentData()

        self.viewmodel.update_draft(
            name=self.name_input.text(),
            priority=self.prio_spin.value(),
            selector_type=sel_type,
            selector_value=self.value_input.text(),
            action_type=action_type,
            condition_type=cond_type,
            failure_behavior=fail_type,
        )

    def _on_validation_changed(self, is_valid: bool, error_msg: str) -> None:
        self.save_btn.setEnabled(is_valid)
        self.error_label.setText(error_msg if not is_valid else "")

    def _on_save_clicked(self) -> None:
        is_valid, _ = self.viewmodel.validate()
        if is_valid:
            self._saved_rule = self.viewmodel.build_rule()
            self.accept()

    def _select_combo_data(self, combo: QComboBox, value: object) -> None:
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                break
