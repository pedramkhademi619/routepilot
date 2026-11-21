"""Diagnostics View for policy evaluation and sanitized support bundles."""

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton

from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.ui.style import ThemeManager
from routepilot.ui.viewmodels.diagnostics_viewmodel import DiagnosticsViewModel
from routepilot.ui.views.base_page import BasePage
from routepilot.ui.widgets.card import Card


class DiagnosticsView(BasePage):
    """Interactive policy evaluation and diagnostic bundle export."""

    def __init__(self, viewmodel: DiagnosticsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self._result: PolicyEvaluationResult | None = None

        self.sim_card = Card()
        input_row = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setClearButtonEnabled(True)
        self.target_input.returnPressed.connect(self._on_evaluate_clicked)
        self.eval_btn = QPushButton()
        self.eval_btn.setObjectName("primaryButton")
        self.eval_btn.clicked.connect(self._on_evaluate_clicked)
        input_row.addWidget(self.target_input, 1)
        input_row.addWidget(self.eval_btn)
        self.sim_card.body.addLayout(input_row)

        self.result_title = QLabel()
        self.result_title.setObjectName("resultTitle")
        self.result_title.setWordWrap(True)
        self.result_desc = QLabel()
        self.result_desc.setObjectName("mutedLabel")
        self.result_desc.setWordWrap(True)
        self.sim_card.body.addWidget(self.result_title)
        self.sim_card.body.addWidget(self.result_desc)
        self.content.addWidget(self.sim_card)

        self.bundle_card = Card()
        self.bundle_desc = QLabel()
        self.bundle_desc.setObjectName("mutedLabel")
        self.bundle_desc.setWordWrap(True)
        self.export_btn = QPushButton()
        self.export_btn.setObjectName("secondaryButton")
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_status = QLabel()
        self.export_status.setObjectName("mutedLabel")
        self.export_status.setWordWrap(True)
        export_row = QHBoxLayout()
        export_row.addWidget(self.export_btn)
        export_row.addStretch()
        self.bundle_card.body.addWidget(self.bundle_desc)
        self.bundle_card.body.addLayout(export_row)
        self.bundle_card.body.addWidget(self.export_status)
        self.content.addWidget(self.bundle_card)
        self.content.addStretch()

        self.viewmodel.evaluation_completed.connect(self._render_result)

    def retranslate_ui(self) -> None:
        t = self.i18n.t
        self.header.set_text(t("diagnostics.title"), t("diagnostics.subtitle"))
        self.sim_card.set_title(t("diagnostics.sim_title"))
        self.target_input.setPlaceholderText(t("diagnostics.input_placeholder"))
        self.eval_btn.setText(t("diagnostics.eval_btn"))
        self.bundle_card.set_title(t("diagnostics.bundle_title"))
        self.bundle_desc.setText(t("diagnostics.bundle_desc"))
        self.export_btn.setText(t("diagnostics.export_btn"))
        if self._result:
            self._render_result(self._result)
        else:
            self._set_result_state("", t("diagnostics.awaiting"), t("diagnostics.awaiting_desc"))

    def _on_evaluate_clicked(self) -> None:
        target = self.target_input.text().strip()
        if target:
            self.viewmodel.evaluate_target(target)

    def _render_result(self, result: PolicyEvaluationResult) -> None:
        t = self.i18n.t
        self._result = result
        details = [result.explanation]
        if result.target_connection and not result.is_blocked:
            conn = result.target_connection
            label = self.i18n.ltr(f"{conn.id} ({conn.interface})")
            details.append(t("diagnostics.result_egress", conn=label))
        details += result.conflicts
        if result.is_blocked:
            title = t("diagnostics.result_action", action=t("diagnostics.result_blocked"))
            state = "blocked"
        else:
            title = t("diagnostics.result_action", action=t(f"action.{result.action.value}"))
            state = "routed" if result.matched_rule else ""
        self._set_result_state(state, title, "\n\n".join(details))

    def _set_result_state(self, state: str, title: str, description: str) -> None:
        self.result_title.setProperty("state", state)
        ThemeManager.repolish(self.result_title)
        self.result_title.setText(title)
        self.result_desc.setText(description)

    def _on_export_clicked(self) -> None:
        t = self.i18n.t
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("diagnostics.save_dialog_title"),
            str(Path.home() / "routepilot-diagnostics.json"),
            "JSON (*.json)",
        )
        if not file_path:
            return
        Path(file_path).write_text(self.viewmodel.export_sanitized_bundle(), encoding="utf-8")
        self.export_status.setText(t("diagnostics.export_saved", path=file_path))
