"""Network connection domain entity."""

from pydantic import BaseModel, Field

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig


class NetworkConnection(BaseModel):
    """Entity representing a Linux network or VPN connection."""

    id: str = Field(..., description="Human-readable connection name e.g. Home-WiFi")
    uuid: str = Field(..., description="Stable unique identifier (RFC 4122 UUID)")
    interface: str = Field(..., description="Kernel interface name e.g. wlo1, vpn0")
    kind: ConnectionKind = Field(
        default=ConnectionKind.UNKNOWN, description="Connection type classification"
    )
    is_vpn: bool = Field(default=False, description="True if this is a virtual private network")
    is_default: bool = Field(
        default=False, description="True if IPv4 default route passes through this connection"
    )
    is_default6: bool = Field(
        default=False, description="True if IPv6 default route passes through this connection"
    )
    state: ConnectionState = Field(
        default=ConnectionState.ACTIVATED, description="Current connection state"
    )
    ip4_config: IPConfig | None = Field(default=None, description="IPv4 configuration")
    ip6_config: IPConfig | None = Field(default=None, description="IPv6 configuration")
    metric: int = Field(default=100, description="Routing metric for default gateway")
    server_endpoint: str | None = Field(
        default=None,
        description="For VPNs: remote transport server IP to protect against recursive routing loops",
    )

    @property
    def is_eligible_direct(self) -> bool:
        """Determines if this connection can act as direct (non-VPN) physical internet egress."""
        return (
            not self.is_vpn
            and self.kind in (ConnectionKind.PHYSICAL_WIFI, ConnectionKind.PHYSICAL_ETHERNET)
            and self.state == ConnectionState.ACTIVATED
            and self.ip4_config is not None
            and self.ip4_config.gateway is not None
        )

    @property
    def primary_ipv4(self) -> str | None:
        """Extracts the first IPv4 address without subnet mask."""
        if self.ip4_config and self.ip4_config.addresses:
            return self.ip4_config.addresses[0].split("/")[0]
        return None
