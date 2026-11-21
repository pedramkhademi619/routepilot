"""Port interface for netfilter (nftables) packet filtering."""

from abc import ABC, abstractmethod


class FirewallPort(ABC):
    """Port interface for the isolated ``table inet routepilot``."""

    @abstractmethod
    def apply_ruleset(self, ruleset_content: str) -> None:
        """Atomically replaces table inet routepilot with ``ruleset_content``."""

    @abstractmethod
    def flush_routepilot_table(self) -> None:
        """Removes only table inet routepilot without affecting system firewalls."""

    @abstractmethod
    def is_table_present(self) -> bool:
        """Checks if table inet routepilot currently exists in the kernel."""
