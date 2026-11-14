"""Diagnostics View for policy evaluation, route tracing, and sanitized log export."""

from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.diagnostics_viewmodel import DiagnosticsViewModel


class DiagnosticsView(QWidget):
    """View providing interactive policy evaluation simulation and diagnostic bundle export."""

    def __init__(self, viewmodel: DiagnosticsViewModel) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.i18n = TranslationManager.instance()

        self._setup_ui()
        self.viewmodel.evaluation_completed.connect(self._render_result)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        title_box = QVBoxLayout()
        self.title = QLabel("Diagnostics & Route Evaluation")
        self.title.setObjectName("titleLabel")
        self.subtitle = QLabel(
            "Verify how traffic to any destination IP or domain is evaluated against your active policies."
        )
        self.subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        layout.addLayout(title_box)

        # Simulation Card
        self.sim_card = QFrame()
        self.sim_card.setObjectName("card")
        sim_layout = QVBoxLayout(self.sim_card)
        self.sim_title = QLabel("Simulate Policy Evaluation")
        self.sim_title.setObjectName("cardTitle")
        sim_layout.addWidget(self.sim_title)

        input_row = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(
            "Enter destination IP or domain (e.g. 198.51.100.1 or example.com)..."
        )
        self.target_input.returnPressed.connect(self._on_evaluate_clicked)
        input_row.addWidget(self.target_input)

        self.eval_btn = QPushButton("Evaluate Path")
        self.eval_btn.setObjectName("primaryButton")
        self.eval_btn.clicked.connect(self._on_evaluate_clicked)
        input_row.addWidget(self.eval_btn)
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

        layout.addWidget(self.sim_card)

        # Export Bundle Card
        self.bundle_card = QFrame()
        self.bundle_card.setObjectName("card")
        bundle_layout = QVBoxLayout(self.bundle_card)
        self.bundle_title = QLabel("Sanitized Support Bundle")
        self.bundle_title.setObjectName("cardTitle")
        self.bundle_desc = QLabel(
            "Export an anonymized JSON report containing active interface types, metrics, and rule "
            "definitions. All passwords, authentication tokens, and user credentials are automatically stripped."
        )
        self.bundle_desc.setWordWrap(True)
        self.bundle_desc.setStyleSheet("color: #A0AEC0;")

        self.export_btn = QPushButton("Export Sanitized Bundle (.json)")
        self.export_btn.setObjectName("secondaryButton")
        self.export_btn.clicked.connect(self._on_export_clicked)

        bundle_layout.addWidget(self.bundle_title)
        bundle_layout.addWidget(self.bundle_desc)
        bundle_layout.addWidget(self.export_btn)
        layout.addWidget(self.bundle_card)

        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates texts in DiagnosticsView."""
        t = self.i18n.tr
        self.title.setText(t("diagnostics.title"))
        self.subtitle.setText(t("diagnostics.subtitle"))
        self.sim_title.setText(t("diagnostics.sim_title"))
        self.target_input.setPlaceholderText(t("diagnostics.input_placeholder"))
        self.eval_btn.setText(t("diagnostics.eval_btn"))
        self.bundle_title.setText(t("diagnostics.bundle_title"))
        self.bundle_desc.setText(t("diagnostics.bundle_desc"))
        self.export_btn.setText(t("diagnostics.export_btn"))

    def _on_evaluate_clicked(self) -> None:
        target = self.target_input.text().strip()
        if target:
            self.viewmodel.evaluate_target(target)

    def _render_result(self, result: PolicyEvaluationResult) -> None:
        is_fa = self.i18n.current_language == "fa"
        if result.is_blocked:
            self.result_title.setText(
                "نتیجه: مسدود شد (ترافیک بلاک گردید)"
                if is_fa
                else "Result: BLOCKED (Traffic Dropped)"
            )
            self.result_title.setStyleSheet("color: #FC8181; font-weight: 700;")
        else:
            action_name = result.action.value.replace("_", " ").upper()
            self.result_title.setText(
                f"نتیجه ارزیابی: {action_name}" if is_fa else f"Result: {action_name}"
            )
            self.result_title.setStyleSheet("color: #68D391; font-weight: 700;")

        explanation = result.explanation
        if result.conflicts:
            explanation += "\n\n" + "\n".join(result.conflicts)
        self.result_desc.setText(explanation)

    def _on_export_clicked(self) -> None:
        is_fa = self.i18n.current_language == "fa"
        content = self.viewmodel.export_sanitized_bundle()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره بسته گزارش تشخیصی سیستم" if is_fa else "Save Sanitized Diagnostic Bundle",
            "routepilot_diagnostics.json",
            "JSON Files (*.json)",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
