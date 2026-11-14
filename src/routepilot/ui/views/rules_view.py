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

from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel


class RulesView(QWidget):
    """View presenting the interactive table of policy routing rules."""

    def __init__(
        self, viewmodel: RulesViewModel, on_edit_rule: Callable[[RoutingRule | None], None]
    ) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_edit_rule = on_edit_rule

        self._setup_ui()
        self.viewmodel.rules_updated.connect(self._render_table)
        self._render_table()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header with Add button
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Traffic Rules")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Define which domains, IP ranges, or applications bypass VPN or use specific connections."
        )
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)

        header_row.addStretch()

        apply_btn = QPushButton("⚡ Apply to Kernel")
        apply_btn.setObjectName("primaryButton")
        apply_btn.setStyleSheet("background-color: #276749; color: #FFFFFF; font-weight: 600;")
        apply_btn.clicked.connect(self._on_apply_clicked)
        header_row.addWidget(apply_btn)

        add_btn = QPushButton("+ Create Rule")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(lambda: self.on_edit_rule(None))
        header_row.addWidget(add_btn)

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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _render_table(self) -> None:
        rules = self.viewmodel.get_rules()
        self.table.setRowCount(len(rules))

        for row, rule in enumerate(rules):
            # 1. State / Toggle
            state_item = QTableWidgetItem("Active" if rule.enabled else "Disabled")
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, state_item)

            # 2. Priority
            prio_item = QTableWidgetItem(str(rule.priority))
            prio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, prio_item)

            # 3. Name
            name_item = QTableWidgetItem(rule.name)
            self.table.setItem(row, 2, name_item)

            # 4. Target Selector
            sel_text = f"{rule.selector.type.value}: {rule.selector.value}"
            sel_item = QTableWidgetItem(sel_text)
            self.table.setItem(row, 3, sel_item)

            # 5. Action
            action_text = rule.action.type.value.replace("_", " ").title()
            action_item = QTableWidgetItem(action_text)
            self.table.setItem(row, 4, action_item)

            # 6. Condition
            cond_text = rule.condition.type.value.replace("_", " ").title()
            cond_item = QTableWidgetItem(cond_text)
            self.table.setItem(row, 5, cond_item)

            # 7. Action Controls widget
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            toggle_btn = QPushButton("Disable" if rule.enabled else "Enable")
            toggle_btn.setObjectName("secondaryButton")
            toggle_btn.clicked.connect(lambda _, r_id=rule.id: self.viewmodel.toggle_rule(r_id))
            btn_layout.addWidget(toggle_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("secondaryButton")
            edit_btn.clicked.connect(lambda _, r=rule: self.on_edit_rule(r))
            btn_layout.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setObjectName("dangerButton")
            del_btn.clicked.connect(lambda _, r_id=rule.id: self.viewmodel.delete_rule(r_id))
            btn_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, btn_widget)

    def _on_apply_clicked(self) -> None:
        """Invokes the routepilot-apply privileged helper via pkexec."""
        subprocess.Popen(["/home/pedram/.local/bin/routepilot-apply"])
