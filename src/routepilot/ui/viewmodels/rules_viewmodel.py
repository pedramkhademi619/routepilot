"""ViewModel for the Rules management screen."""

from datetime import UTC, datetime

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.ports.policy_repository_port import PolicyRepositoryPort


class RulesViewModel(QObject):
    """ViewModel managing the listing, filtering, and state modification of routing rules."""

    rules_updated = pyqtSignal()
    # Emitted after the saved policy changed (not for filtering) so it can be re-applied.
    policy_changed = pyqtSignal()

    def __init__(self, policy_repo: PolicyRepositoryPort) -> None:
        super().__init__()
        self._policy_repo = policy_repo
        self._filter_query: str = ""

    @property
    def filter_query(self) -> str:
        return self._filter_query

    def get_rules(self) -> list[RoutingRule]:
        """Returns sorted rules, filtered by the current query if specified."""
        sorted_rules = self._policy_repo.load_policy().sort_by_priority()
        if not self._filter_query:
            return sorted_rules

        q = self._filter_query.lower()
        return [
            r
            for r in sorted_rules
            if q in r.name.lower()
            or q in r.selector.value.lower()
            or q in r.action.type.value.lower()
        ]

    def has_rules(self) -> bool:
        return bool(self._policy_repo.load_policy().rules)

    def set_filter(self, query: str) -> None:
        """Sets the search query and emits update signal."""
        self._filter_query = query.strip()
        self.rules_updated.emit()

    def toggle_rule(self, rule_id: str) -> None:
        """Toggles the enabled status of a rule and persists."""
        doc = self._policy_repo.load_policy()
        for r in doc.rules:
            if r.id == rule_id:
                r.enabled = not r.enabled
                break
        self._save(doc)

    def delete_rule(self, rule_id: str) -> None:
        """Deletes a rule by ID and persists."""
        doc = self._policy_repo.load_policy()
        doc.rules = [r for r in doc.rules if r.id != rule_id]
        self._save(doc)

    def save_or_update_rule(self, rule: RoutingRule) -> None:
        """Inserts a new rule or replaces an existing one by ID."""
        doc = self._policy_repo.load_policy()
        existing_idx = next((i for i, r in enumerate(doc.rules) if r.id == rule.id), -1)
        if existing_idx >= 0:
            doc.rules[existing_idx] = rule
        else:
            doc.rules.append(rule)
        self._save(doc)

    def clear_all_rules(self) -> None:
        self._save(PolicyDocument(updated_at=datetime.now(UTC).isoformat(), rules=[]))

    def get_rule_by_id(self, rule_id: str) -> RoutingRule | None:
        doc = self._policy_repo.load_policy()
        return next((r for r in doc.rules if r.id == rule_id), None)

    def _save(self, doc: PolicyDocument) -> None:
        self._policy_repo.save_policy(doc)
        self.rules_updated.emit()
        self.policy_changed.emit()
