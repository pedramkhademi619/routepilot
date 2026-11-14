"""Nftables firewall adapter implementing FirewallPort."""

import logging
import shutil
import subprocess

from routepilot.domain.ports.firewall_port import FirewallPort

logger = logging.getLogger(__name__)


class NftablesFirewallAdapter(FirewallPort):
    """Adapter managing the isolated 'table inet routepilot' using /usr/sbin/nft."""

    TABLE_NAME = "routepilot"
    FAMILY = "inet"

    def __init__(self, nft_path: str = "/usr/sbin/nft") -> None:
        self.nft_path = shutil.which("nft") or nft_path

    def apply_ruleset(self, ruleset_content: str) -> None:
        """Applies a complete ruleset atomically via standard input to nft -f -."""
        logger.info("Applying atomic nftables ruleset (%d bytes)...", len(ruleset_content))
        proc = subprocess.run(
            [self.nft_path, "-f", "-"],
            input=ruleset_content,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            logger.error("nft -f - failed: %s", proc.stderr.strip())
            raise RuntimeError(f"nftables application failed: {proc.stderr.strip()}")
        logger.info("nftables ruleset applied successfully.")

    def flush_routepilot_table(self) -> None:
        """Purges table inet routepilot."""
        logger.info("Deleting table inet %s...", self.TABLE_NAME)
        proc = subprocess.run(
            [self.nft_path, "delete", "table", self.FAMILY, self.TABLE_NAME],
            capture_output=True,
            text=True,
            check=False,
        )
        # returncode 1 is expected if table does not exist
        if proc.returncode == 0:
            logger.info("Deleted table inet %s.", self.TABLE_NAME)

    def add_set_elements(self, set_name: str, elements: list[str]) -> None:
        """Adds elements to a named set."""
        if not elements:
            return
        elems_str = ", ".join(elements)
        cmd = [
            self.nft_path,
            "add",
            "element",
            self.FAMILY,
            self.TABLE_NAME,
            set_name,
            f"{{ {elems_str} }}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            logger.warning("Failed to add elements to %s: %s", set_name, proc.stderr.strip())

    def remove_set_elements(self, set_name: str, elements: list[str]) -> None:
        """Removes elements from a named set."""
        if not elements:
            return
        elems_str = ", ".join(elements)
        cmd = [
            self.nft_path,
            "delete",
            "element",
            self.FAMILY,
            self.TABLE_NAME,
            set_name,
            f"{{ {elems_str} }}",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            logger.warning("Failed to remove elements from %s: %s", set_name, proc.stderr.strip())

    def is_table_present(self) -> bool:
        """Checks if table inet routepilot exists."""
        proc = subprocess.run(
            [self.nft_path, "list", "table", self.FAMILY, self.TABLE_NAME],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0
