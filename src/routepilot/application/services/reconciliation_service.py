"""Reconciliation service: converges kernel state to a plan, with journaling and rollback."""

import logging

from routepilot.application.services.routing_layout import RoutingLayout
from routepilot.domain.exceptions.rollback_error import RollbackError
from routepilot.domain.models.routepilot_plan import RoutePilotPlan
from routepilot.domain.ports.dns_resolver_port import DnsResolverPort
from routepilot.domain.ports.firewall_port import FirewallPort
from routepilot.domain.ports.plan_journal_port import PlanJournalPort
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Applies plans idempotently and tears RoutePilot state down on failure or request.

    Applying is a diff against what the kernel currently holds in RoutePilot-owned tables, so
    re-applying the same plan is a no-op and stale routes from earlier plans are removed
    without a window where traffic falls back to the VPN.
    """

    def __init__(
        self,
        routing_port: PolicyRoutingPort,
        firewall_port: FirewallPort,
        dns_port: DnsResolverPort | None = None,
        journal: PlanJournalPort | None = None,
    ) -> None:
        self.routing_port = routing_port
        self.firewall_port = firewall_port
        self.dns_port = dns_port
        self.journal = journal

    def apply_plan(self, plan: RoutePilotPlan) -> bool:
        """Converges kernel state to ``plan``; rolls back everything if any step fails."""
        logger.info("Applying RoutePilot plan: %s", plan.plan_id)
        previous = self.journal.load() if self.journal else None
        self._journal_save(plan, "staged")

        try:
            self._sync_firewall(plan)
            self._sync_routes(plan)
            self._sync_rules(plan)
        except Exception as e:
            logger.error("Plan application failed: %s. Rolling back...", e)
            try:
                self.teardown(plan, previous)
            except RollbackError as rollback_error:
                logger.error("Rollback incomplete: %s", rollback_error)
            raise RollbackError(f"Application failed and was rolled back: {e}") from e

        self._sync_split_dns(plan, previous)
        self._journal_save(plan, "committed")
        logger.info("Plan %s committed successfully.", plan.plan_id)
        return True

    def teardown(self, *plans: RoutePilotPlan | None) -> None:
        """Removes every kernel resource RoutePilot owns (and split DNS of ``plans``)."""
        errors: list[str] = []

        priorities = (*RoutingLayout.owned_priorities(), *RoutingLayout.LEGACY_RULE_PRIORITIES)
        for priority in priorities:
            for family in RoutingLayout.FAMILIES:
                try:
                    self.routing_port.delete_rule(priority, family)
                except Exception as e:
                    errors.append(f"ip rule prio {priority} (IPv{family}): {e}")

        for table_id in RoutingLayout.owned_tables():
            for family in RoutingLayout.FAMILIES:
                try:
                    self.routing_port.flush_table(table_id, family)
                except Exception as e:
                    errors.append(f"table {table_id} (IPv{family}): {e}")

        try:
            self.firewall_port.flush_routepilot_table()
        except Exception as e:
            errors.append(f"nftables table inet routepilot: {e}")

        if self.dns_port:
            for plan in plans:
                for iface, domains in (plan.split_dns if plan else {}).items():
                    try:
                        self.dns_port.reset_split_dns(iface, domains)
                    except Exception as e:
                        errors.append(f"split DNS on {iface}: {e}")

        if self.journal:
            self.journal.clear()

        if errors:
            raise RollbackError("; ".join(errors))

    def emergency_reset(self) -> None:
        """Purges all RoutePilot kernel state, including split DNS of the journaled plan."""
        self.teardown(self.journal.load() if self.journal else None)

    def _sync_firewall(self, plan: RoutePilotPlan) -> None:
        if plan.nft_ruleset:
            self.firewall_port.apply_ruleset(plan.nft_ruleset)
        else:
            self.firewall_port.flush_routepilot_table()

    def _sync_routes(self, plan: RoutePilotPlan) -> None:
        for table_id in RoutingLayout.owned_tables():
            for family in RoutingLayout.FAMILIES:
                desired = {r.key: r for r in plan.routes_in(table_id, family)}
                for route in desired.values():
                    self.routing_port.replace_route(route)
                for stale in self.routing_port.list_routes(table_id, family):
                    if stale.key not in desired:
                        self.routing_port.delete_route(stale)

    def _sync_rules(self, plan: RoutePilotPlan) -> None:
        desired = {(r.priority, r.family): r for r in plan.rules}
        for priority in RoutingLayout.owned_priorities():
            for family in RoutingLayout.FAMILIES:
                rule = desired.get((priority, family))
                if rule:
                    self.routing_port.replace_rule(rule)
                else:
                    self.routing_port.delete_rule(priority, family)
        for priority in RoutingLayout.LEGACY_RULE_PRIORITIES:
            self.routing_port.delete_rule(priority, 4)

    def _sync_split_dns(self, plan: RoutePilotPlan, previous: RoutePilotPlan | None) -> None:
        """Best effort: DNS steering never blocks routing changes from being committed."""
        if not self.dns_port:
            return
        before = previous.split_dns if previous else {}
        for iface in sorted(set(before) | set(plan.split_dns)):
            wanted = plan.split_dns.get(iface, [])
            try:
                if wanted:
                    self.dns_port.configure_split_dns(iface, wanted, before.get(iface))
                elif before.get(iface):
                    self.dns_port.reset_split_dns(iface, before[iface])
            except Exception as e:
                logger.warning("Split DNS update on %s failed: %s", iface, e)

    def _journal_save(self, plan: RoutePilotPlan, status: str) -> None:
        if not self.journal:
            return
        try:
            self.journal.save(plan, status)
        except Exception as e:
            logger.warning("Failed to write transaction journal: %s", e)
