"""Routing table entry model."""

from pydantic import BaseModel, Field


class RouteEntry(BaseModel):
    """Routing table entry."""

    destination: str = Field(..., description="Destination CIDR e.g. 0.0.0.0/0 or 192.168.1.0/24")
    gateway: str | None = Field(default=None, description="Next hop gateway IP")
    interface: str = Field(..., description="Egress network interface e.g. wlo1")
    metric: int = Field(default=100, description="Route priority metric")
    table_id: int = Field(default=254, description="Routing table ID (254 = main)")
    family: int = Field(default=4, description="Address family (4 or 6)")
