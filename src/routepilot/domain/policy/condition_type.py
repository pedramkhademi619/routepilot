"""Activation condition type enum."""

from enum import StrEnum


class ConditionType(StrEnum):
    """When a rule should activate."""

    ALWAYS = "always"
    SPECIFIC_VPN_ACTIVE = "specific_vpn_active"
    ANY_VPN_ACTIVE = "any_vpn_active"
    NETWORK_PROFILE_ACTIVE = "network_profile_active"
