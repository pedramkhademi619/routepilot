"""Port interface for packet marking and netfilter firewall."""

from abc import ABC, abstractmethod


class FirewallPort(ABC):
    """Port interface for interacting with netfilter/nftables."""

    @abstractmethod
    def apply_ruleset(self, ruleset_content: str) -> None:
        """Applies a complete ruleset atomically within table inet routepilot."""

    @abstractmethod
    def flush_routepilot_table(self) -> None:
        """Purges only table inet routepilot without affecting system firewalls."""

    @abstractmethod
    def add_set_elements(self, set_name: str, elements: list[str]) -> None:
        """Adds IP addresses or subnets to a named nftables set."""

    @abstractmethod
    def remove_set_elements(self, set_name: str, elements: list[str]) -> None:
        """Removes IP addresses or subnets from a named nftables set."""

    @abstractmethod
    def is_table_present(self) -> bool:
        """Checks if table inet routepilot currently exists in the kernel."""
