"""RoutePilot Domain Layer."""

from routepilot.domain.exceptions.rollback_error import RollbackError
from routepilot.domain.exceptions.routepilot_error import RoutePilotError
from routepilot.domain.exceptions.rule_conflict_error import RuleConflictError
from routepilot.domain.exceptions.target_unavailable_error import TargetUnavailableError
from routepilot.domain.exceptions.validation_error import ValidationError
from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.policy.action_type import ActionType
from routepilot.domain.policy.activation_condition import ActivationCondition
from routepilot.domain.policy.condition_type import ConditionType
from routepilot.domain.policy.failure_behavior import FailureBehavior
from routepilot.domain.policy.fallback_policy import FallbackPolicy
from routepilot.domain.policy.policy_action import PolicyAction
from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.policy.traffic_selector import TrafficSelector

__all__ = [
    "ActionType",
    "ActivationCondition",
    "ConditionType",
    "ConnectionKind",
    "ConnectionState",
    "FailureBehavior",
    "FallbackPolicy",
    "IPConfig",
    "NetworkConnection",
    "PolicyAction",
    "PolicyDocument",
    "RollbackError",
    "RouteEntry",
    "RoutePilotError",
    "RoutingRule",
    "RuleConflictError",
    "SelectorType",
    "TargetUnavailableError",
    "TrafficSelector",
    "ValidationError",
]
