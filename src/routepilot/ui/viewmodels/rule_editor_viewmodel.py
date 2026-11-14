"""ViewModel for the Rule Editor dialog."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.activation_condition import ActivationCondition
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector


class RuleEditorViewModel(QObject):
    """ViewModel maintaining state, validation, and real-time preview for rule editing."""

    validation_changed = pyqtSignal(bool, str)
    preview_changed = pyqtSignal(str)

    def __init__(self, existing_rule: RoutingRule | None = None) -> None:
        super().__init__()
        self.rule_id: str | None = existing_rule.id if existing_rule else None
        self.name: str = existing_rule.name if existing_rule else ""
        self.priority: int = existing_rule.priority if existing_rule else 50
        self.selector_type: SelectorType = (
            existing_rule.selector.type if existing_rule else SelectorType.DOMAIN
        )
        self.selector_value: str = existing_rule.selector.value if existing_rule else ""
        self.action_type: ActionType = (
            existing_rule.action.type if existing_rule else ActionType.USE_DIRECT
        )
        self.target_vpn_uuid: str | None = (
            existing_rule.action.target_connection_uuid if existing_rule else None
        )
        self.condition_type: ConditionType = (
            existing_rule.condition.type if existing_rule else ConditionType.ALWAYS
        )
        self.failure_behavior: FailureBehavior = (
            existing_rule.fallback.behavior if existing_rule else FailureBehavior.BLOCK
        )

    def update_draft(
        self,
        name: str,
        priority: int,
        selector_type: SelectorType,
        selector_value: str,
        action_type: ActionType,
        condition_type: ConditionType,
        failure_behavior: FailureBehavior,
    ) -> None:
        """Updates internal state and validates."""
        self.name = name.strip()
        self.priority = priority
        self.selector_type = selector_type
        self.selector_value = selector_value.strip()
        self.action_type = action_type
        self.condition_type = condition_type
        self.failure_behavior = failure_behavior

        is_valid, error = self.validate()
        self.validation_changed.emit(is_valid, error)
        if is_valid:
            rule = self.build_rule()
            self.preview_changed.emit(rule.human_summary())
        else:
            self.preview_changed.emit(f"Rule draft incomplete: {error}")

    def validate(self) -> tuple[bool, str]:
        """Validates all fields in the draft rule."""
        if not self.name:
            return False, "Rule name is required."
        if not self.selector_value:
            return False, "Target selector value is required."

        try:
            sel = TrafficSelector(type=self.selector_type, value=self.selector_value)
            sel.validate_selector()
        except Exception as e:
            return False, f"Invalid selector: {e}"

        return True, ""

    def build_rule(self) -> RoutingRule:
        """Builds a verified RoutingRule domain entity."""
        selector = TrafficSelector(type=self.selector_type, value=self.selector_value)
        action = PolicyAction(
            type=self.action_type,
            target_connection_uuid=self.target_vpn_uuid,
        )
        condition = ActivationCondition(type=self.condition_type)
        fallback = FallbackPolicy(behavior=self.failure_behavior)

        rule = RoutingRule(
            name=self.name,
            priority=self.priority,
            selector=selector,
            condition=condition,
            action=action,
            fallback=fallback,
        )
        if self.rule_id:
            rule.id = self.rule_id
        return rule
