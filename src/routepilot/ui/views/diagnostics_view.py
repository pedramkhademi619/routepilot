"""Diagnostics View for policy evaluation, route tracing, and sanitized log export."""

from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.ui.viewmodels.diagnostics_viewmodel import DiagnosticsViewModel


class DiagnosticsView(QWidget):
    """View providing interactive policy evaluation simulation and diagnostic bundle export."""

    def __init__(self, viewmodel: DiagnosticsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel

        self._setup_ui()
        self.viewmodel.evaluation_completed.connect(self._render_result)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        title_box = QVBoxLayout()
        title = QLabel("Diagnostics & Route Evaluation")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Verify how traffic to any destination IP or domain is evaluated against your active policies."
        )
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Simulation Card
        sim_card = QFrame()
        sim_card.setObjectName("card")
        sim_layout = QVBoxLayout(sim_card)
        sim_title = QLabel("Simulate Policy Evaluation")
        sim_title.setObjectName("cardTitle")
        sim_layout.addWidget(sim_title)

        input_row = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(
            "Enter destination IP or domain (e.g. 198.51.100.1 or example.com)..."
        )
        self.target_input.returnPressed.connect(self._on_evaluate_clicked)
        input_row.addWidget(self.target_input)

        eval_btn = QPushButton("Evaluate Path")
        eval_btn.setObjectName("primaryButton")
        eval_btn.clicked.connect(self._on_evaluate_clicked)
        input_row.addWidget(eval_btn)
        sim_layout.addLayout(input_row)

        # Result box
        self.result_frame = QFrame()
        res_layout = QVBoxLayout(self.result_frame)
        self.result_title = QLabel("Awaiting evaluation...")
        self.result_title.setObjectName("cardTitle")
        self.result_desc = QLabel(
            "Enter a destination above to trace its effective kernel route and winning rule."
        )
        self.result_desc.setWordWrap(True)
        self.result_desc.setStyleSheet("color: #A0AEC0;")
        res_layout.addWidget(self.result_title)
        res_layout.addWidget(self.result_desc)
        sim_layout.addWidget(self.result_frame)

        layout.addWidget(sim_card)

        # Export Bundle Card
        bundle_card = QFrame()
        bundle_card.setObjectName("card")
        bundle_layout = QVBoxLayout(bundle_card)
        bundle_title = QLabel("Sanitized Support Bundle")
        bundle_title.setObjectName("cardTitle")
        bundle_desc = QLabel(
            "Export an anonymized JSON report containing active interface types, metrics, and rule "
            "definitions. All passwords, authentication tokens, and user credentials are automatically stripped."
        )
        bundle_desc.setWordWrap(True)
        bundle_desc.setStyleSheet("color: #A0AEC0;")

        export_btn = QPushButton("Export Sanitized Bundle (.json)")
        export_btn.setObjectName("secondaryButton")
        export_btn.clicked.connect(self._on_export_clicked)

        bundle_layout.addWidget(bundle_title)
        bundle_layout.addWidget(bundle_desc)
        bundle_layout.addWidget(export_btn)
        layout.addWidget(bundle_card)

        layout.addStretch()

    def _on_evaluate_clicked(self) -> None:
        target = self.target_input.text().strip()
        if target:
            self.viewmodel.evaluate_target(target)

    def _render_result(self, result: PolicyEvaluationResult) -> None:
        if result.is_blocked:
            self.result_title.setText("Result: BLOCKED (Traffic Dropped)")
            self.result_title.setStyleSheet("color: #FC8181; font-weight: 700;")
        else:
            action_name = result.action.value.replace("_", " ").upper()
            self.result_title.setText(f"Result: {action_name}")
            self.result_title.setStyleSheet("color: #68D391; font-weight: 700;")

        explanation = result.explanation
        if result.conflicts:
            explanation += "\n\n" + "\n".join(result.conflicts)
        self.result_desc.setText(explanation)

    def _on_export_clicked(self) -> None:
        content = self.viewmodel.export_sanitized_bundle()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sanitized Diagnostic Bundle",
            "routepilot_diagnostics.json",
            "JSON Files (*.json)",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
