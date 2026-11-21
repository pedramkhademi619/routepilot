"""Routing table entry model."""

import ipaddress

from pydantic import BaseModel, Field, field_validator, model_validator

from routepilot.domain.models.route_type import RouteType


class RouteEntry(BaseModel):
    """Routing table entry."""

    destination: str = Field(..., description="Destination CIDR e.g. 0.0.0.0/0 or 192.168.1.0/24")
    gateway: str | None = Field(default=None, description="Next hop gateway IP")
    interface: str | None = Field(default=None, description="Egress network interface e.g. wlo1")
    metric: int = Field(default=100, description="Route priority metric")
    table_id: int = Field(default=254, description="Routing table ID (254 = main)")
    family: int = Field(default=4, description="Address family (4 or 6), derived from destination")
    route_type: RouteType = Field(default=RouteType.UNICAST, description="Kernel route type")

    @field_validator("destination")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        """Normalizes bare addresses and host bits into canonical CIDR notation."""
        return ipaddress.ip_network(value.strip(), strict=False).with_prefixlen

    @model_validator(mode="after")
    def derive_family(self) -> "RouteEntry":
        self.family = ipaddress.ip_network(self.destination).version
        return self

    @property
    def key(self) -> tuple[int, int, str]:
        """Identity of the route inside the kernel: (table, family, destination)."""
        return (self.table_id, self.family, self.destination)
