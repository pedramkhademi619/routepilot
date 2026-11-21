"""IP layer configuration model."""

from pydantic import BaseModel, Field


class IPConfig(BaseModel):
    """IP layer configuration details for an interface."""

    addresses: list[str] = Field(
        default_factory=list, description="Assigned CIDR addresses, e.g. 192.168.1.173/24"
    )
    gateway: str | None = Field(default=None, description="Default gateway IP address")
    dns_servers: list[str] = Field(
        default_factory=list, description="List of configured DNS servers"
    )
    domains: list[str] = Field(default_factory=list, description="Search domains")
    default_route_metric: int | None = Field(
        default=None, description="Metric of this link's default route, if it has one"
    )
