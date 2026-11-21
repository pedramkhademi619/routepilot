"""Guided Rule Editor Dialog with real-time validation and plain-language summary."""

from collections.abc import Sequence
from enum import StrEnum

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.rule_editor_viewmodel import RuleEditorViewModel

EDITABLE_SELECTORS = (
    SelectorType.DOMAIN,
    SelectorType.DOMAIN_AND_SUBDOMAINS,
    SelectorType.IP_ADDRESS,
    SelectorType.CIDR,
)
EDITABLE_ACTIONS = (
    ActionType.USE_DIRECT,
    ActionType.USE_SELECTED_VPN,
    ActionType.BLOCK,
    ActionType.FOLLOW_SYSTEM,
)
EDITABLE_CONDITIONS = (
    ConditionType.ALWAYS,
    ConditionType.ANY_VPN_ACTIVE,
    ConditionType.SPECIFIC_VPN_ACTIVE,
)
EDITABLE_FALLBACKS = (FailureBehavior.BLOCK, FailureBehavior.FOLLOW_SYSTEM)


class RuleEditorDialog(QDialog):
    """Modal dialog for creating and editing RoutePilot policy rules."""

    def __init__(
        self,
        existing_rule: RoutingRule | None = None,
        vpns: list[NetworkConnection] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.i18n = TranslationManager.instance()
        self.viewmodel = RuleEditorViewModel(existing_rule, vpns)
        self._saved_rule: RoutingRule | None = None
        t = self.i18n.t
        self.setWindowTitle(t("editor.title_new" if self.viewmodel.is_new else "editor.title_edit"))
        self.setMinimumWidth(360)
        self.resize(560, 600)

        self._setup_ui()
        self._connect_signals()
        self._on_input_changed()

    def get_rule(self) -> RoutingRule | None:
        return self._saved_rule

    def _setup_ui(self) -> None:
        t = self.i18n.t
        vm = self.viewmodel
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 22, 24, 12)
        layout.setSpacing(16)

        header = QLabel(t("editor.title_new" if vm.is_new else "editor.title_edit"))
        header.setObjectName("titleLabel")
        layout.addWidget(header)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.name_input = QLineEdit(vm.name)
        self.name_input.setPlaceholderText(t("editor.name_placeholder"))
        form.addRow(t("editor.name"), self.name_input)

        selectors = list(EDITABLE_SELECTORS)
        if vm.selector_type not in selectors:
            selectors.append(vm.selector_type)  # keep legacy/experimental values editable
        self.selector_combo = self._combo("selector", selectors, vm.selector_type)
        form.addRow(t("editor.target_type"), self.selector_combo)

        self.value_input = QLineEdit(vm.selector_value)
        form.addRow(t("editor.target_value"), self.value_input)

        self.action_combo = self._combo("action", EDITABLE_ACTIONS, vm.action_type)
        form.addRow(t("editor.action"), self.action_combo)

        self.vpn_combo = self._vpn_combo(vm.target_vpn_uuid, allow_any=True)
        self.vpn_label = QLabel(t("editor.target_vpn"))
        form.addRow(self.vpn_label, self.vpn_combo)

        self.condition_combo = self._combo("condition", EDITABLE_CONDITIONS, vm.condition_type)
        form.addRow(t("editor.condition"), self.condition_combo)

        self.condition_vpn_combo = self._vpn_combo(vm.condition_vpn_uuid, allow_any=False)
        self.condition_vpn_label = QLabel(t("editor.condition_vpn"))
        form.addRow(self.condition_vpn_label, self.condition_vpn_combo)

        self.fallback_combo = self._combo("fallback", EDITABLE_FALLBACKS, vm.failure_behavior)
        form.addRow(t("editor.failure"), self.fallback_combo)

        self.prio_spin = QSpinBox()
        self.prio_spin.setRange(1, 9999)
        self.prio_spin.setValue(vm.priority)
        self.prio_spin.setToolTip(t("editor.priority_hint"))
        line_edit = self.prio_spin.lineEdit()
        if line_edit is not None:
            line_edit.setTextMargins(8, 0, 8, 0)  # QSS padding does not reach the inner editor
        form.addRow(t("editor.priority"), self.prio_spin)
        layout.addLayout(form)

        preview_title = QLabel(t("editor.explanation"))
        preview_title.setObjectName("cardTitle")
        self.preview_label = QLabel()
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(True)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(preview_title)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.error_label)
        layout.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.setContentsMargins(24, 8, 24, 18)
        self.save_btn = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_btn = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if self.save_btn is not None:
            self.save_btn.setText(t("editor.save"))
            self.save_btn.setObjectName("primaryButton")
        if cancel_btn is not None:
            cancel_btn.setText(t("common.cancel"))
            cancel_btn.setObjectName("secondaryButton")
        self.buttons.accepted.connect(self._on_save_clicked)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

    def _combo(self, prefix: str, values: Sequence[StrEnum], current: StrEnum) -> QComboBox:
        combo = QComboBox()
        for value in values:
            combo.addItem(self.i18n.t(f"{prefix}.{value.value}"), value)
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        return combo

    def _vpn_combo(self, current_uuid: str | None, allow_any: bool) -> QComboBox:
        combo = QComboBox()
        if allow_any:
            combo.addItem(self.i18n.t("editor.any_vpn"), None)
        for vpn in self.viewmodel.vpns:
            combo.addItem(f"{vpn.id} ({vpn.interface})", vpn.uuid)
        if current_uuid and combo.findData(current_uuid) < 0:
            combo.addItem(current_uuid, current_uuid)  # VPN configured earlier but offline now
        index = combo.findData(current_uuid)
        combo.setCurrentIndex(max(index, 0))
        return combo

    def _connect_signals(self) -> None:
        for line_edit in (self.name_input, self.value_input):
            line_edit.textChanged.connect(self._on_input_changed)
        for combo in (
            self.selector_combo,
            self.action_combo,
            self.vpn_combo,
            self.condition_combo,
            self.condition_vpn_combo,
            self.fallback_combo,
        ):
            combo.currentIndexChanged.connect(self._on_input_changed)
        self.prio_spin.valueChanged.connect(self._on_input_changed)
        self.viewmodel.validation_changed.connect(self._on_validation_changed)
        self.viewmodel.preview_changed.connect(self.preview_label.setText)

    def _on_input_changed(self) -> None:
        selector = self.selector_combo.currentData()
        action = self.action_combo.currentData()
        condition = self.condition_combo.currentData()
        self.value_input.setPlaceholderText(self.i18n.t(f"editor.placeholder.{selector.value}"))

        needs_vpn = action == ActionType.USE_SELECTED_VPN
        needs_condition_vpn = condition == ConditionType.SPECIFIC_VPN_ACTIVE
        for widget in (self.vpn_label, self.vpn_combo):
            widget.setVisible(needs_vpn)
        for widget in (self.condition_vpn_label, self.condition_vpn_combo):
            widget.setVisible(needs_condition_vpn)

        self.viewmodel.update_draft(
            name=self.name_input.text(),
            priority=self.prio_spin.value(),
            selector_type=selector,
            selector_value=self.value_input.text(),
            action_type=action,
            condition_type=condition,
            failure_behavior=self.fallback_combo.currentData(),
            target_vpn_uuid=self.vpn_combo.currentData() if needs_vpn else None,
            condition_vpn_uuid=self.condition_vpn_combo.currentData()
            if needs_condition_vpn
            else None,
        )

    def _on_validation_changed(self, is_valid: bool, error_msg: str) -> None:
        if self.save_btn is not None:
            self.save_btn.setEnabled(is_valid)
        self.error_label.setText(error_msg)
        self.error_label.setVisible(bool(error_msg))

    def _on_save_clicked(self) -> None:
        is_valid, _ = self.viewmodel.validate()
        if is_valid:
            self._saved_rule = self.viewmodel.build_rule()
            self.accept()
