"""ViewModel for Diagnostics and route verification."""

import json
from datetime import UTC, datetime

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.application.services.discovery_service import DiscoveryService
from routepilot.application.services.policy_evaluation_result import PolicyEvaluationResult
from routepilot.application.services.policy_evaluator import PolicyEvaluator
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort


class DiagnosticsViewModel(QObject):
    """ViewModel for evaluating policy routing simulation and generating support bundles."""

    evaluation_completed = pyqtSignal(object)

    def __init__(
        self, discovery_service: DiscoveryService, policy_repo: PolicyRepositoryPort
    ) -> None:
        super().__init__()
        self._discovery_service = discovery_service
        self._policy_repo = policy_repo

    def evaluate_target(self, target: str, app_id: str | None = None) -> PolicyEvaluationResult:
        """Runs the deterministic policy evaluator against live connections."""
        doc = self._policy_repo.load_policy()
        conns = self._discovery_service.get_cached_connections()
        evaluator = PolicyEvaluator(doc.rules)
        res = evaluator.evaluate(target.strip(), conns, app_id=app_id)
        self.evaluation_completed.emit(res)
        return res

    def export_sanitized_bundle(self) -> str:
        """Exports a sanitized JSON diagnostic bundle with personal details redacted."""
        conns = self._discovery_service.get_cached_connections()
        doc = self._policy_repo.load_policy()

        sanitized_conns = []
        for c in conns:
            sanitized_conns.append(
                {
                    "kind": c.kind.value,
                    "is_vpn": c.is_vpn,
                    "interface": c.interface,
                    "state": c.state.value,
                    "metric": c.metric,
                    "is_eligible_direct": c.is_eligible_direct,
                }
            )

        sanitized_rules = []
        for r in doc.rules:
            sanitized_rules.append(
                {
                    "name": r.name,
                    "priority": r.priority,
                    "enabled": r.enabled,
                    "selector_type": r.selector.type.value,
                    "action": r.action.type.value,
                    "condition": r.condition.type.value,
                    "fallback": r.fallback.behavior.value,
                }
            )

        bundle = {
            "timestamp": datetime.now(UTC).isoformat(),
            "routepilot_version": "0.1.0",
            "active_connections": sanitized_conns,
            "configured_rules": sanitized_rules,
        }
        return json.dumps(bundle, indent=2)
