"""Nftables firewall adapter implementing FirewallPort."""

import logging
import shutil
import subprocess

from routepilot.domain.ports.firewall_port import FirewallPort

logger = logging.getLogger(__name__)


class NftablesFirewallAdapter(FirewallPort):
    """Adapter managing the isolated 'table inet routepilot' using the nft binary."""

    TABLE_NAME = "routepilot"
    FAMILY = "inet"

    def __init__(self, nft_path: str = "/usr/sbin/nft") -> None:
        self.nft_path = shutil.which("nft") or nft_path

    def apply_ruleset(self, ruleset_content: str) -> None:
        """Replaces the table in one nft transaction: either all of it applies or nothing."""
        # Declaring then deleting the table first makes the load idempotent instead of
        # appending duplicate rules on every apply.
        script = (
            f"table {self.FAMILY} {self.TABLE_NAME}\n"
            f"delete table {self.FAMILY} {self.TABLE_NAME}\n" + ruleset_content
        )
        logger.info("Applying atomic nftables ruleset (%d bytes)...", len(script))
        proc = self._run("-f", "-", stdin=script)
        if proc.returncode != 0:
            raise RuntimeError(f"nftables application failed: {proc.stderr.strip()}")

    def flush_routepilot_table(self) -> None:
        if not self.is_table_present():
            return
        proc = self._run("delete", "table", self.FAMILY, self.TABLE_NAME)
        if proc.returncode != 0:
            raise RuntimeError(f"Could not delete nftables table: {proc.stderr.strip()}")
        logger.info("Deleted table %s %s.", self.FAMILY, self.TABLE_NAME)

    def is_table_present(self) -> bool:
        return self._run("list", "table", self.FAMILY, self.TABLE_NAME).returncode == 0

    def _run(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.nft_path, *args],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
