"""Rules View for searching, inspecting, and managing traffic policy rules."""

from collections.abc import Callable

from PyQt6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.ui.icons import Icons
from routepilot.ui.viewmodels.rules_viewmodel import RulesViewModel
from routepilot.ui.views.base_page import BasePage


class RulesView(BasePage):
    """Interactive table of policy routing rules."""

    COL_ENABLED, COL_NAME, COL_TARGET, COL_ACTION, COL_CONDITION, COL_PRIORITY, COL_CONTROLS = (
        range(7)
    )
    # Columns hidden when the table is narrower than the given width (least important first).
    HIDE_BELOW = {COL_CONDITION: 780, COL_PRIORITY: 640, COL_ACTION: 520}

    def __init__(
        self,
        viewmodel: RulesViewModel,
        on_edit_rule: Callable[[RoutingRule | None], None],
        on_apply: Callable[[], None],
    ) -> None:
        super().__init__(scrollable=False)
        self.viewmodel = viewmodel
        self.on_edit_rule = on_edit_rule
        self._icon_colors = {"muted": "#9AA3B2", "danger_fg": "#FCA5A5", "on_primary": "#FFFFFF"}

        self.apply_btn = QPushButton()
        self.apply_btn.setObjectName("secondaryButton")
        self.apply_btn.clicked.connect(on_apply)
        self.add_btn = QPushButton()
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(lambda: self.on_edit_rule(None))
        for btn in (self.apply_btn, self.add_btn):
            btn.setIconSize(QSize(16, 16))
            self.header.add_action(btn)

        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.viewmodel.set_filter)
        self.content.addWidget(self.search_input)

        self.stack = QStackedWidget()
        self.table = self._build_table()
        self.table.installEventFilter(self)
        self.stack.addWidget(self.table)
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("emptyTitle")
        self.empty_body = QLabel()
        self.empty_body.setObjectName("mutedLabel")
        for label in (self.empty_title, self.empty_body):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(label)
        self.stack.addWidget(self.empty_state)
        self.content.addWidget(self.stack, 1)

        self.viewmodel.rules_updated.connect(self._render_table)

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(0, 7)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.cellDoubleClicked.connect(self._on_row_double_clicked)
        v_header = table.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(44)
        header = table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(False)
            header.setHighlightSections(False)
            header.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter
            )
            fixed = QHeaderView.ResizeMode.Fixed
            content = QHeaderView.ResizeMode.ResizeToContents
            stretch = QHeaderView.ResizeMode.Stretch
            modes = {
                self.COL_ENABLED: fixed,
                self.COL_NAME: stretch,
                self.COL_TARGET: stretch,
                self.COL_ACTION: content,
                self.COL_CONDITION: content,
                self.COL_PRIORITY: content,
                self.COL_CONTROLS: fixed,
            }
            for column, mode in modes.items():
                header.setSectionResizeMode(column, mode)
            table.setColumnWidth(self.COL_ENABLED, 56)
            table.setColumnWidth(self.COL_CONTROLS, 84)
        return table

    def retranslate_ui(self) -> None:
        t = self.i18n.t
        self.header.set_text(t("rules.title"), t("rules.subtitle"))
        self.add_btn.setText(t("common.create_rule"))
        self.search_input.setPlaceholderText(t("rules.filter_placeholder"))
        self.set_applying(not self.apply_btn.isEnabled())
        self.table.setHorizontalHeaderLabels(
            [
                t("rules.col_enabled"),
                t("rules.col_name"),
                t("rules.col_target"),
                t("rules.col_action"),
                t("rules.col_condition"),
                t("rules.col_priority"),
                t("rules.col_actions"),
            ]
        )
        self._render_table()

    def refresh_icons(self, palette: dict[str, str]) -> None:
        self._icon_colors = palette
        self.add_btn.setIcon(Icons.get("plus", palette["on_primary"]))
        self.apply_btn.setIcon(Icons.get("apply", palette["muted"]))
        self._render_table()

    def set_applying(self, busy: bool) -> None:
        self.apply_btn.setEnabled(not busy)
        self.apply_btn.setText(self.i18n.t("common.applying" if busy else "common.apply"))

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:  # noqa: N802
        if watched is self.table and event is not None and event.type() == QEvent.Type.Resize:
            self._update_visible_columns()
        return bool(super().eventFilter(watched, event))

    def _update_visible_columns(self) -> None:
        width = self.table.width()
        for column, min_width in self.HIDE_BELOW.items():
            self.table.setColumnHidden(column, width < min_width)

    def _render_table(self) -> None:
        t = self.i18n.t
        rules = self.viewmodel.get_rules()
        if not rules:
            query = self.viewmodel.filter_query
            self.empty_title.setText(
                t("rules.no_match", query=query) if query else t("rules.empty_title")
            )
            self.empty_body.setVisible(not query)
            self.empty_body.setText(t("rules.empty_body"))
            self.stack.setCurrentWidget(self.empty_state)
            return

        self.stack.setCurrentWidget(self.table)
        self.table.setRowCount(0)  # releases (hides and deletes) the previous row widgets
        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self.table.setCellWidget(row, self.COL_ENABLED, self._toggle_cell(rule))
            target = self._display_target(rule)
            values = {
                self.COL_NAME: rule.name,
                self.COL_TARGET: self.i18n.ltr(target),
                self.COL_ACTION: t(f"action.{rule.action.type.value}"),
                self.COL_CONDITION: t(f"condition.{rule.condition.type.value}"),
                self.COL_PRIORITY: str(rule.priority),
            }
            for column, text in values.items():
                item = QTableWidgetItem(text)
                item.setToolTip(
                    f"{rule.name}\n{t(f'selector.{rule.selector.type.value}')}: {target}"
                )
                alignment = (
                    Qt.AlignmentFlag.AlignCenter
                    if column == self.COL_PRIORITY
                    else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeading
                )
                item.setTextAlignment(alignment)
                if not rule.enabled:
                    item.setForeground(self.table.palette().placeholderText())
                self.table.setItem(row, column, item)
            self.table.setCellWidget(row, self.COL_CONTROLS, self._controls_cell(rule))
        self._update_visible_columns()

    def _toggle_cell(self, rule: RoutingRule) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box = QCheckBox()
        box.setChecked(rule.enabled)
        box.setToolTip(self.i18n.t("rules.toggle_tip"))
        box.setAccessibleName(f"{self.i18n.t('rules.toggle_tip')}: {rule.name}")
        box.toggled.connect(
            lambda _checked, r_id=rule.id: self._defer(self.viewmodel.toggle_rule, r_id)
        )
        layout.addWidget(box)
        return cell

    def _controls_cell(self, rule: RoutingRule) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for icon, color_key, tip_key, handler in (
            (
                "edit",
                "muted",
                "common.edit",
                lambda _=False, r=rule: self._defer(self.on_edit_rule, r),
            ),
            (
                "delete",
                "danger_fg",
                "common.delete",
                lambda _=False, r=rule: self._defer(self._confirm_delete, r),
            ),
        ):
            btn = QToolButton()
            btn.setObjectName("iconButton")
            btn.setIcon(Icons.get(icon, self._icon_colors.get(color_key, "#9AA3B2")))
            btn.setIconSize(QSize(18, 18))
            btn.setToolTip(self.i18n.t(tip_key))
            btn.setAccessibleName(f"{self.i18n.t(tip_key)}: {rule.name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
        return cell

    @staticmethod
    def _defer(handler: Callable[..., None], *args: object) -> None:
        """Runs ``handler`` after the current event: re-rendering deletes the clicked widget."""
        QTimer.singleShot(0, lambda: handler(*args))

    def _confirm_delete(self, rule: RoutingRule) -> None:
        t = self.i18n.t
        answer = QMessageBox.question(
            self,
            t("rules.confirm_delete_title"),
            t("rules.confirm_delete_body", name=rule.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.viewmodel.delete_rule(rule.id)

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        rules = self.viewmodel.get_rules()
        if 0 <= row < len(rules):
            self.on_edit_rule(rules[row])

    @staticmethod
    def _display_target(rule: RoutingRule) -> str:
        if rule.selector.type == SelectorType.DOMAIN_AND_SUBDOMAINS:
            return f"*.{rule.selector.root_domain}"
        return rule.selector.value
