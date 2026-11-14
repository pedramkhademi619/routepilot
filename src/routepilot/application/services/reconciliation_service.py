"""Reconciliation service managing staged application, journal logging, and rollback."""

import json
import logging
import os

from routepilot.application.services.routepilot_plan import RoutePilotPlan
from routepilot.domain.exceptions.rollback_error import RollbackError
from routepilot.domain.ports.firewall_port import FirewallPort
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Manages transactional application, rollback, and crash recovery of RoutePilot state."""

    DEFAULT_JOURNAL_PATH = "/run/routepilot/journal.json"

    def __init__(
        self,
        routing_port: PolicyRoutingPort,
        firewall_port: FirewallPort,
        journal_path: str | None = None,
    ) -> None:
        self.routing_port = routing_port
        self.firewall_port = firewall_port
        self.journal_path = journal_path or self._resolve_journal_path()
        self._active_plan: RoutePilotPlan | None = None

    def apply_plan(self, plan: RoutePilotPlan) -> bool:
        """Applies a compiled RoutePilotPlan with staged rollback protection."""
        logger.info("Applying RoutePilot plan: %s", plan.plan_id)
        self._write_journal(plan, status="staged")

        try:
            # 1. Apply nftables ruleset atomically
            self.firewall_port.apply_ruleset(plan.nft_ruleset_content)

            # 2. Populate routing tables
            for table_id, route in plan.tables_to_create.items():
                self.routing_port.add_routing_table_route(table_id, route)

            # 3. Apply IP rules
            for rule in plan.rules_to_add:
                self.routing_port.add_policy_rule(
                    table_id=rule["table_id"],
                    priority=rule["priority"],
                    fwmark=rule["fwmark"],
                    fwmask=rule.get("fwmask", 0x00FF0000),
                    family=rule.get("family", 4),
                )

            self._active_plan = plan
            self._write_journal(plan, status="committed")
            logger.info("Plan %s committed successfully.", plan.plan_id)
            return True

        except Exception as e:
            logger.error("Plan application failed: %s. Initiating immediate rollback...", e)
            self.rollback_plan(plan)
            raise RollbackError(f"Application failed and was rolled back: {e}") from e

    def rollback_plan(self, plan: RoutePilotPlan) -> None:
        """Reverts kernel mutations introduced by the plan."""
        logger.warning("Rolling back plan: %s", plan.plan_id)
        errors = []

        # 1. Remove IP rules
        for prio in plan.rollback_rule_priorities:
            try:
                self.routing_port.remove_policy_rule(prio)
            except Exception as e:
                errors.append(f"Failed to remove ip rule prio {prio}: {e}")

        # 2. Flush custom routing tables
        for table_id in plan.rollback_tables:
            try:
                self.routing_port.flush_table_routes(table_id)
            except Exception as e:
                errors.append(f"Failed to flush table {table_id}: {e}")

        # 3. Flush nftables table inet routepilot
        try:
            self.firewall_port.flush_routepilot_table()
        except Exception as e:
            errors.append(f"Failed to flush nftables routepilot table: {e}")

        self._active_plan = None
        self._clear_journal()

        if errors:
            raise RollbackError("; ".join(errors))

    def emergency_reset(self) -> None:
        """Purges any residual RoutePilot kernel state."""
        try:
            self.firewall_port.flush_routepilot_table()
        except Exception:
            pass

        for prio in range(10000, 10100):
            try:
                self.routing_port.remove_policy_rule(prio)
            except Exception:
                pass

        for table_id in range(10001, 10100):
            try:
                self.routing_port.flush_table_routes(table_id)
            except Exception:
                pass

        self._clear_journal()

    def _resolve_journal_path(self) -> str:
        run_dir = "/run/routepilot"
        if os.path.exists(run_dir) and os.access(run_dir, os.W_OK):
            return self.DEFAULT_JOURNAL_PATH
        user_runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
        fallback_dir = os.path.join(user_runtime, "routepilot")
        os.makedirs(fallback_dir, exist_ok=True)
        return os.path.join(fallback_dir, "journal.json")

    def _write_journal(self, plan: RoutePilotPlan, status: str) -> None:
        try:
            os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
            data = {
                "plan_id": plan.plan_id,
                "status": status,
                "plan": plan.model_dump(),
            }
            with open(self.journal_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to write transaction journal: %s", e)

    def _clear_journal(self) -> None:
        try:
            if os.path.exists(self.journal_path):
                os.remove(self.journal_path)
        except Exception:
            pass
