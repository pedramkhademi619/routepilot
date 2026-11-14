"""Systemd-resolved adapter implementing DnsResolverPort."""

import asyncio
import logging
import shutil
import socket
import subprocess

from routepilot.domain.ports.dns_resolver_port import DnsResolverPort

logger = logging.getLogger(__name__)


class SystemdResolvedAdapter(DnsResolverPort):
    """Adapter managing split DNS routing domains and resolution via systemd-resolved."""

    def __init__(self) -> None:
        self.resolvectl_path = shutil.which("resolvectl") or "/usr/bin/resolvectl"

    async def resolve_domain(self, domain: str) -> list[str]:
        """Resolves IPv4 and IPv6 addresses for a domain name asynchronously."""
        loop = asyncio.get_running_loop()
        try:
            addr_info = await loop.run_in_executor(
                None, lambda: socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
            )
            ips = list({str(info[4][0]) for info in addr_info})
            return ips
        except Exception as e:
            logger.warning("DNS resolution failed for %s: %s", domain, e)
            return []

    def configure_split_dns(self, interface: str, domains: list[str]) -> None:
        """Sets routing domains (~domain) on the specified link."""
        if not domains:
            return
        routing_domains = [f"~{d.lstrip('~')}" for d in domains]
        cmd = [self.resolvectl_path, "domain", interface, *routing_domains]
        logger.info("Configuring split DNS on %s: %s", interface, " ".join(routing_domains))
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            logger.warning("resolvectl domain failed on %s: %s", interface, proc.stderr.strip())

    def reset_split_dns(self, interface: str) -> None:
        """Clears routing domains from the link."""
        cmd = [self.resolvectl_path, "domain", interface, ""]
        logger.info("Resetting split DNS on %s", interface)
        subprocess.run(cmd, capture_output=True, text=True, check=False)
