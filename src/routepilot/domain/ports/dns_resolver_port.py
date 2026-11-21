"""Port interface for DNS resolution and split DNS management."""

from abc import ABC, abstractmethod


class DnsResolverPort(ABC):
    """Port interface for resolving domains and managing split DNS routing domains."""

    @abstractmethod
    async def resolve_domain(self, domain: str, interface: str | None = None) -> list[str]:
        """Resolves A and AAAA records, preferably via the DNS servers of ``interface``."""

    @abstractmethod
    def configure_split_dns(
        self, interface: str, domains: list[str], previous: list[str] | None = None
    ) -> None:
        """Routes DNS queries for ``domains`` to ``interface``, replacing ``previous``."""

    @abstractmethod
    def reset_split_dns(self, interface: str, domains: list[str]) -> None:
        """Removes RoutePilot's routing domains from a link, keeping everything else."""
