"""Policy action classification enum."""

from enum import StrEnum


class ActionType(StrEnum):
    """Action to take on matched traffic."""

    FOLLOW_SYSTEM = "follow_system"
    USE_DIRECT = "use_direct"
    USE_SELECTED_VPN = "use_selected_vpn"
    BLOCK = "block"
    EXCLUDE_VPN = "exclude_vpn"
