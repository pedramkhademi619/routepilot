"""Rules View for searching, inspecting, and managing traffic policy rules."""

import subprocess
from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel


class RulesView(QWidget):
    """View presenting the interactive table of policy routing rules."""

    def __init__(
        self, viewmodel: RulesViewModel, on_edit_rule: Callable[[RoutingRule | None], None]
    ) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_edit_rule = on_edit_rule
        self.i18n = TranslationManager.instance()

        self._setup_ui()
        self.viewmodel.rules_updated.connect(self._render_table)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header with Add button
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title = QLabel("Traffic Rules")
        self.title.setObjectName("titleLabel")
        self.subtitle = QLabel(
            "Define which domains, IP ranges, or applications bypass VPN or use specific connections."
        )
        self.subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header_row.addLayout(title_box)

        header_row.addStretch()

        self.apply_btn = QPushButton("⚡ Apply to Kernel")
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.setStyleSheet("background-color: #276749; color: #FFFFFF; font-weight: 600;")
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        header_row.addWidget(self.apply_btn)

        self.add_btn = QPushButton("+ Create Rule")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(lambda: self.on_edit_rule(None))
        header_row.addWidget(self.add_btn)

        layout.addLayout(header_row)

        # Search bar
        search_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter rules by name, domain, or IP...")
        self.search_input.textChanged.connect(self.viewmodel.set_filter)
        search_box.addWidget(self.search_input)
        layout.addLayout(search_box)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["State", "Prio", "Rule Name", "Target Selector", "Action", "Condition", "Controls"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        v_header = self.table.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(44)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(False)

            # 0: State (Fixed width badge)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 95)

            # 1: Prio (Fixed width)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(1, 55)

            # 2: Rule Name (Interactive with 170px default)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(2, 170)

            # 3: Target Selector (STRETCH to take all remaining flexible width)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

            # 4: Action (Interactive with 120px default)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(4, 120)

            # 5: Condition (Interactive with 130px default)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(5, 130)

            # 6: Controls (Fixed width for action buttons, never stretches)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(6, 220)

        layout.addWidget(self.table)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates headers, placeholders, and table items."""
        t = self.i18n.t
        self.title.setText(t("rules.title"))
        self.subtitle.setText(t("rules.subtitle"))
        self.apply_btn.setText(t("common.apply"))
        self.add_btn.setText(t("common.create_rule"))
        self.search_input.setPlaceholderText(t("common.filter_placeholder"))

        self.table.setHorizontalHeaderLabels([
            t("rules.col_state"),
            t("rules.col_prio"),
            t("rules.col_name"),
            t("rules.col_target"),
            t("rules.col_action"),
            t("rules.col_condition"),
            t("rules.col_controls"),
        ])
        self._render_table()

    def _render_table(self) -> None:
        t = self.i18n.t
        is_fa = self.i18n.current_language == "fa"
        rules = self.viewmodel.get_rules()
        self.table.setRowCount(len(rules))

        for row, rule in enumerate(rules):
            # 1. State / Toggle Badge
            badge_widget = QWidget()
            badge_layout = QHBoxLayout(badge_widget)
            badge_layout.setContentsMargins(6, 4, 6, 4)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state_text = (
                ("🟢 فعال" if rule.enabled else "⚪ غیرفعال")
                if is_fa
                else ("🟢 Active" if rule.enabled else "⚪ Disabled")
            )
            badge = QLabel(state_text)
            badge.setObjectName("badgeDirect" if rule.enabled else "badgeOffline")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(badge)
            self.table.setCellWidget(row, 0, badge_widget)

            # 2. Priority
            prio_item = QTableWidgetItem(str(rule.priority))
            prio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, prio_item)

            # 3. Name
            name_item = QTableWidgetItem(rule.name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 2, name_item)

            # 4. Target Selector
            sel_text = f"{rule.selector.type.value}: {rule.selector.value}"
            sel_item = QTableWidgetItem(sel_text)
            sel_item.setToolTip(sel_text)
            sel_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 3, sel_item)

            # 5. Action
            action_text = self._format_action(rule.action.type, is_fa)
            action_item = QTableWidgetItem(action_text)
            action_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 4, action_item)

            # 6. Condition
            cond_text = self._format_condition(rule.condition.type, is_fa)
            cond_item = QTableWidgetItem(cond_text)
            cond_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, 5, cond_item)

            # 7. Action Controls widget
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if rule.enabled:
                toggle_label = "⏸ غیرفعال‌سازی" if is_fa else "⏸ Disable"
                toggle_tip = "کلیک کنید تا این قانون غیرفعال شود" if is_fa else "Click to disable this rule"
                toggle_btn_obj = "secondaryButton"
            else:
                toggle_label = "▶ فعال‌سازی" if is_fa else "▶ Enable"
                toggle_tip = "کلیک کنید تا این قانون فعال شود" if is_fa else "Click to enable this rule"
                toggle_btn_obj = "primaryButton"

            toggle_btn = QPushButton(toggle_label)
            toggle_btn.setToolTip(toggle_tip)
            toggle_btn.setObjectName(toggle_btn_obj)
            toggle_btn.setFixedWidth(82 if is_fa else 74)
            toggle_btn.setFixedHeight(28)
            toggle_btn.clicked.connect(lambda _, r_id=rule.id: self._on_toggle_rule(r_id))
            btn_layout.addWidget(toggle_btn)

            edit_btn = QPushButton(t("common.edit"))
            edit_btn.setObjectName("secondaryButton")
            edit_btn.setFixedWidth(54)
            edit_btn.setFixedHeight(28)
            edit_btn.clicked.connect(lambda _, r=rule: self.on_edit_rule(r))
            btn_layout.addWidget(edit_btn)

            del_btn = QPushButton(t("common.delete"))
            del_btn.setObjectName("dangerButton")
            del_btn.setFixedWidth(56)
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, r_id=rule.id: self._on_delete_rule(r_id))
            btn_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, btn_widget)

    def _on_toggle_rule(self, rule_id: str) -> None:
        """Toggles rule and immediately updates kernel routing state."""
        self.viewmodel.toggle_rule(rule_id)
        self._on_apply_clicked()

    def _on_delete_rule(self, rule_id: str) -> None:
        """Deletes rule and immediately updates kernel routing state."""
        self.viewmodel.delete_rule(rule_id)
        self._on_apply_clicked()

    def _format_action(self, action_type: ActionType, is_fa: bool) -> str:
        if is_fa:
            mapping = {
                ActionType.USE_DIRECT: "عبور مستقیم",
                ActionType.USE_SELECTED_VPN: "فقط وی‌پی‌ان",
                ActionType.BLOCK: "مسدودسازی",
                ActionType.FOLLOW_SYSTEM: "پیش‌فرض سیستم",
            }
            return mapping.get(action_type, action_type.value)
        return action_type.value.replace("_", " ").title()

    def _format_condition(self, cond_type: ConditionType, is_fa: bool) -> str:
        if is_fa:
            mapping = {
                ConditionType.ALWAYS: "همیشه فعال",
                ConditionType.ANY_VPN_ACTIVE: "هنگام اتصال VPN",
                ConditionType.SPECIFIC_VPN_ACTIVE: "اتصال VPN خاص",
            }
            return mapping.get(cond_type, cond_type.value)
        return cond_type.value.replace("_", " ").title()

    def _on_apply_clicked(self) -> None:
        """Invokes the routepilot-apply privileged helper via pkexec."""
        subprocess.Popen(["/home/pedram/.local/bin/routepilot-apply"])
