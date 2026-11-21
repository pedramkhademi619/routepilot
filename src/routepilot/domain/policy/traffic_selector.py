"""Traffic selector model."""

import ipaddress
import re

from pydantic import BaseModel, Field, field_validator

from routepilot.domain.policy.selector_type import SelectorType

_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
)


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
            url_match = re.match(r"^https?://([^/:\s]+)", clean)
            if url_match:
                clean = url_match.group(1)

        return clean

    @property
    def is_network(self) -> bool:
        """True for IP address and CIDR selectors."""
        return self.type in (SelectorType.IP_ADDRESS, SelectorType.CIDR)

    @property
    def is_domain(self) -> bool:
        """True for domain and domain-with-subdomains selectors."""
        return self.type in (SelectorType.DOMAIN, SelectorType.DOMAIN_AND_SUBDOMAINS)

    @property
    def root_domain(self) -> str:
        """Domain without wildcard prefix and trailing dot, lower-cased."""
        return self.value.lower().lstrip("*.").rstrip(".")

    def hostnames(self) -> list[str]:
        """Hostnames to resolve for a domain selector (subdomains cannot be enumerated)."""
        if not self.is_domain:
            return []
        root = self.root_domain
        names = [root]
        if self.type == SelectorType.DOMAIN_AND_SUBDOMAINS and not root.startswith("www."):
            names.append(f"www.{root}")
        return names

    def validate_selector(self) -> None:
        """Performs strict validation based on selector type."""
        if self.is_network:
            try:
                network = ipaddress.ip_network(self.value, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid IP/CIDR '{self.value}': {e}") from e
            if self.type == SelectorType.IP_ADDRESS and network.num_addresses != 1:
                raise ValueError(f"'{self.value}' is a subnet; choose the CIDR type instead")

        elif self.is_domain:
            if not _DOMAIN_PATTERN.match(self.root_domain):
                raise ValueError(f"Invalid domain format '{self.value}'")
