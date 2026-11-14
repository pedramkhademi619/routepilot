"""Port interface for DNS resolution and split DNS management."""

from abc import ABC, abstractmethod


class DnsResolverPort(ABC):
    """Port interface for resolving domains and managing split DNS routing domains."""

    @abstractmethod
    async def resolve_domain(self, domain: str) -> list[str]:
        """Resolves A and AAAA records for a domain name."""

    @abstractmethod
    def configure_split_dns(self, interface: str, domains: list[str]) -> None:
        """Configures routing domains (~domain) on a network link."""

    @abstractmethod
    def reset_split_dns(self, interface: str) -> None:
        """Clears RoutePilot split DNS routing domains from a link."""
