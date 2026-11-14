"""Connection classification enum."""

from enum import StrEnum


class ConnectionKind(StrEnum):
    """Classification of network connections."""

    PHYSICAL_WIFI = "wifi"
    PHYSICAL_ETHERNET = "ethernet"
    VPN_WIREGUARD = "wireguard"
    VPN_OPENVPN = "openvpn"
    VPN_GENERIC = "vpn"
    TUN = "tun"
    BRIDGE = "bridge"
    LOOPBACK = "loopback"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"
