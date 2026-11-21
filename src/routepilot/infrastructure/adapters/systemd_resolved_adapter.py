"""Systemd-resolved adapter implementing DnsResolverPort."""

import asyncio
import ipaddress
import logging
import shutil
import socket
import subprocess
from collections.abc import Iterable

from routepilot.domain.ports.dns_resolver_port import DnsResolverPort

logger = logging.getLogger(__name__)


class SystemdResolvedAdapter(DnsResolverPort):
    """Resolves names per link and manages routing domains (``~domain``) via resolvectl."""

    def __init__(self) -> None:
        self.resolvectl_path = shutil.which("resolvectl")

    async def resolve_domain(self, domain: str, interface: str | None = None) -> list[str]:
        if interface and self.resolvectl_path:
            ips = await asyncio.to_thread(self._query_link, domain, interface)
            if ips:
                return ips
        return await asyncio.to_thread(self._getaddrinfo, domain)

    def configure_split_dns(
        self, interface: str, domains: list[str], previous: list[str] | None = None
    ) -> None:
        stale = {self._routing(d) for d in previous or []}
        merged = [d for d in self.link_domains(interface) if d not in stale]
        merged += [self._routing(d) for d in domains if self._routing(d) not in merged]
        self._set_link_domains(interface, merged)

    def reset_split_dns(self, interface: str, domains: list[str]) -> None:
        ours = {self._routing(d) for d in domains}
        self._set_link_domains(
            interface, [d for d in self.link_domains(interface) if d not in ours]
        )

    def link_domains(self, interface: str) -> list[str]:
        """Current search/routing domains of a link, e.g. ``['lan', '~example.com']``."""
        proc = self._resolvectl("domain", interface)
        if proc is None or proc.returncode != 0 or "):" not in proc.stdout:
            return []
        return proc.stdout.split("):", 1)[1].split()

    def _set_link_domains(self, interface: str, domains: list[str]) -> None:
        logger.info("Setting DNS domains on %s: %s", interface, " ".join(domains) or "(none)")
        proc = self._resolvectl("domain", interface, *(domains or [""]))
        if proc is not None and proc.returncode != 0:
            raise RuntimeError(f"resolvectl domain {interface} failed: {proc.stderr.strip()}")

    def _query_link(self, domain: str, interface: str) -> list[str]:
        proc = self._resolvectl("query", "--legend=no", "-i", interface, domain)
        if proc is None or proc.returncode != 0:
            return []
        return self._unique_ips(proc.stdout.replace(",", " ").split())

    def _getaddrinfo(self, domain: str) -> list[str]:
        try:
            infos = socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        except OSError as e:
            logger.warning("DNS resolution failed for %s: %s", domain, e)
            return []
        return self._unique_ips(str(info[4][0]) for info in infos)

    def _resolvectl(self, *args: str) -> subprocess.CompletedProcess[str] | None:
        if not self.resolvectl_path:
            logger.warning("resolvectl not found; split DNS is unavailable.")
            return None
        return subprocess.run(
            [self.resolvectl_path, *args], capture_output=True, text=True, check=False, timeout=15
        )

    @staticmethod
    def _routing(domain: str) -> str:
        return f"~{domain.lstrip('~')}"

    @staticmethod
    def _unique_ips(tokens: Iterable[str]) -> list[str]:
        ips: list[str] = []
        for token in tokens:
            try:
                ip = str(ipaddress.ip_address(token))
            except ValueError:
                continue
            if ip not in ips:
                ips.append(ip)
        return ips
