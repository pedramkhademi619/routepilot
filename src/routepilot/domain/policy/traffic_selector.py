"""Traffic selector model."""

import ipaddress
import re

from pydantic import BaseModel, Field, field_validator

from routepilot.domain.policy.selector_type import SelectorType


class TrafficSelector(BaseModel):
    """Traffic selector definition."""

    type: SelectorType = Field(..., description="Type of traffic selector")
    value: str = Field(..., description="Target value (domain, IP, CIDR, or binary/scope ID)")
    protocol: str | None = Field(
        default=None, description="Optional protocol filter: tcp, udp, or any"
    )
    port_range: str | None = Field(
        default=None, description="Optional port or range e.g. '443' or '8000-8080'"
    )

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Selector value cannot be empty")

        # Automatically clean URL if user pasted one
        if clean.startswith(("http://", "https://")):
            # Extract host portion
            url_match = re.match(r"^https?://([^/:\s]+)", clean)
            if url_match:
                clean = url_match.group(1)

        return clean

    def validate_selector(self) -> None:
        """Performs strict domain validation based on selector type."""
        if self.type in (SelectorType.IP_ADDRESS, SelectorType.CIDR):
            try:
                ipaddress.ip_network(self.value, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid IP/CIDR '{self.value}': {e}") from e

        elif self.type in (SelectorType.DOMAIN, SelectorType.DOMAIN_AND_SUBDOMAINS):
            domain = self.value.lstrip("*.")
            if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
                raise ValueError(f"Invalid domain format '{self.value}'")
