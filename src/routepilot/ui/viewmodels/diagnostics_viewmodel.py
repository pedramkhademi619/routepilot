"""ViewModel for Diagnostics and route verification."""

import json
import platform
from datetime import UTC, datetime

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot import __version__
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
        res = PolicyEvaluator(doc.rules).evaluate(target.strip(), conns, app_id=app_id)
        self.evaluation_completed.emit(res)
        return res

    def export_sanitized_bundle(self) -> str:
        """JSON report without connection names, addresses, rule names or targets."""
        conns = self._discovery_service.get_cached_connections()
        rules = self._policy_repo.load_policy().sort_by_priority()
        bundle = {
            "timestamp": datetime.now(UTC).isoformat(),
            "routepilot_version": __version__,
            "python": platform.python_version(),
            "kernel": platform.release(),
            "active_connections": [
                {
                    "kind": c.kind.value,
                    "is_vpn": c.is_vpn,
                    "interface": c.interface,
                    "state": c.state.value,
                    "metric": c.metric,
                    "is_default": c.is_default,
                    "is_eligible_direct": c.is_eligible_direct,
                    "has_ipv6": c.ip6_config is not None,
                }
                for c in conns
            ],
            "configured_rules": [
                {
                    "priority": r.priority,
                    "enabled": r.enabled,
                    "selector_type": r.selector.type.value,
                    "action": r.action.type.value,
                    "condition": r.condition.type.value,
                    "fallback": r.fallback.behavior.value,
                }
                for r in rules
            ],
        }
        return json.dumps(bundle, indent=2)
