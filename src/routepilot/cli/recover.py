"""Emergency recovery CLI to purge RoutePilot kernel state."""

import sys

from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.infrastructure.adapters.nftables_firewall_adapter import NftablesFirewallAdapter
from routepilot.infrastructure.adapters.pyroute2_routing_adapter import Pyroute2RoutingAdapter


class EmergencyRecoveryCli:
    """CLI tool for resetting kernel routing rules and flushing table inet routepilot."""

    def __init__(self) -> None:
        self.routing_adapter = Pyroute2RoutingAdapter()
        self.firewall_adapter = NftablesFirewallAdapter()
        self.reconciliation = ReconciliationService(self.routing_adapter, self.firewall_adapter)

    def run(self) -> int:
        print("RoutePilot: Initiating emergency state purge...")
        try:
            self.reconciliation.emergency_reset()
            print(
                "Successfully purged table inet routepilot and custom policy tables (10001..10099)."
            )
            return 0
        except Exception as e:
            print(f"Error during recovery: {e}", file=sys.stderr)
            return 1


def main() -> None:
    cli = EmergencyRecoveryCli()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
