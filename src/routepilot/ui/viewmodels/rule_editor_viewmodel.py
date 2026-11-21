"""ViewModel for the Rule Editor dialog."""

from PyQt6.QtCore import QObject, pyqtSignal

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.activation_condition import ActivationCondition
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector
from routepilot.ui.translation_manager import TranslationManager


class RuleEditorViewModel(QObject):
    """ViewModel maintaining state, validation, and real-time preview for rule editing."""

    validation_changed = pyqtSignal(bool, str)
    preview_changed = pyqtSignal(str)

    def __init__(
        self,
        existing_rule: RoutingRule | None = None,
        vpns: list[NetworkConnection] | None = None,
    ) -> None:
        super().__init__()
        self.i18n = TranslationManager.instance()
        self.vpns = vpns or []
        self._existing = existing_rule
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
        self.condition_vpn_uuid: str | None = (
            existing_rule.condition.target_vpn_uuid if existing_rule else None
        )
        self.failure_behavior: FailureBehavior = (
            existing_rule.fallback.behavior if existing_rule else FailureBehavior.BLOCK
        )
        self.enabled: bool = existing_rule.enabled if existing_rule else True

    @property
    def is_new(self) -> bool:
        return self.rule_id is None

    def update_draft(
        self,
        name: str,
        priority: int,
        selector_type: SelectorType,
        selector_value: str,
        action_type: ActionType,
        condition_type: ConditionType,
        failure_behavior: FailureBehavior,
        target_vpn_uuid: str | None = None,
        condition_vpn_uuid: str | None = None,
    ) -> None:
        """Updates internal state and validates."""
        self.name = name.strip()
        self.priority = priority
        self.selector_type = selector_type
        self.selector_value = selector_value.strip()
        self.action_type = action_type
        self.condition_type = condition_type
        self.failure_behavior = failure_behavior
        self.target_vpn_uuid = target_vpn_uuid
        self.condition_vpn_uuid = condition_vpn_uuid

        is_valid, error = self.validate()
        self.validation_changed.emit(is_valid, error)
        self.preview_changed.emit(self.summary() if is_valid else "")

    def validate(self) -> tuple[bool, str]:
        """Validates all fields in the draft rule."""
        t = self.i18n.t
        if not self.name:
            return False, t("editor.error.name_required")
        if not self.selector_value:
            return False, t("editor.error.value_required")
        try:
            TrafficSelector(type=self.selector_type, value=self.selector_value).validate_selector()
        except ValueError as e:
            return False, t("editor.error.invalid_selector", error=str(e).splitlines()[-1])
        if self.condition_type == ConditionType.SPECIFIC_VPN_ACTIVE and not self.condition_vpn_uuid:
            return False, t("editor.error.vpn_required")
        return True, ""

    def summary(self) -> str:
        """Plain-language, translated description of the draft rule."""
        t = self.i18n.t
        value = self.selector_value.lower().lstrip("*.")
        target = f"*.{value}" if self.selector_type == SelectorType.DOMAIN_AND_SUBDOMAINS else value
        action = t(f"action.{self.action_type.value}")
        if self.action_type == ActionType.USE_SELECTED_VPN and self.target_vpn_uuid:
            action += f" ({self._vpn_name(self.target_vpn_uuid)})"
        condition = t(f"condition.{self.condition_type.value}")
        if self.condition_type == ConditionType.SPECIFIC_VPN_ACTIVE and self.condition_vpn_uuid:
            condition += f" ({self._vpn_name(self.condition_vpn_uuid)})"
        return t(
            "editor.summary",
            target=self.i18n.ltr(target),
            action=action,
            condition=condition,
            fallback=t(f"fallback.{self.failure_behavior.value}"),
        )

    def build_rule(self) -> RoutingRule:
        """Builds a verified RoutingRule domain entity, preserving fields the editor hides."""
        base = self._existing
        selector = TrafficSelector(type=self.selector_type, value=self.selector_value)
        action = PolicyAction(
            type=self.action_type,
            target_connection_uuid=(
                self.target_vpn_uuid if self.action_type == ActionType.USE_SELECTED_VPN else None
            ),
            excluded_vpn_uuids=base.action.excluded_vpn_uuids if base else [],
        )
        condition = ActivationCondition(
            type=self.condition_type,
            target_vpn_uuid=(
                self.condition_vpn_uuid
                if self.condition_type == ConditionType.SPECIFIC_VPN_ACTIVE
                else None
            ),
            target_profile_name=base.condition.target_profile_name if base else None,
        )
        fallback = FallbackPolicy(
            behavior=self.failure_behavior,
            alternative_connection_uuid=(
                base.fallback.alternative_connection_uuid if base else None
            ),
            user_consented_fail_open=self.failure_behavior == FailureBehavior.FOLLOW_SYSTEM,
        )
        rule = RoutingRule(
            name=self.name,
            description=base.description if base else None,
            enabled=self.enabled,
            priority=self.priority,
            selector=selector,
            condition=condition,
            action=action,
            fallback=fallback,
        )
        if self.rule_id:
            rule.id = self.rule_id
        return rule

    def _vpn_name(self, uuid: str) -> str:
        return next((v.id for v in self.vpns if v.uuid == uuid), uuid[:8])
