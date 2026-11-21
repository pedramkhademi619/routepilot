"""Use case: turn the saved policy into live kernel routing state."""

import asyncio

from routepilot.application.services.plan_compiler import PlanCompiler
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.models.routepilot_plan import RoutePilotPlan
from routepilot.domain.policy.routing_rule import RoutingRule
from routepilot.domain.ports.dns_resolver_port import DnsResolverPort
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort


class PolicyApplyService:
    """Discovers connections, resolves domains, compiles a plan and reconciles it."""

    def __init__(
        self,
        discovery: NetworkDiscoveryPort,
        resolver: DnsResolverPort,
        reconciliation: ReconciliationService,
        compiler: PlanCompiler | None = None,
    ) -> None:
        self._discovery = discovery
        self._resolver = resolver
        self._reconciliation = reconciliation
        self._compiler = compiler or PlanCompiler()

    async def build_plan(self, rules: list[RoutingRule]) -> RoutePilotPlan:
        """Compiles a plan for ``rules`` against the live network, without applying it."""
        connections = await self._discovery.discover_connections()
        requests = self._compiler.resolution_requests(rules, connections)
        answers = await asyncio.gather(
            *(self._resolver.resolve_domain(host, iface) for host, iface in requests.items())
        )
        resolved = dict(zip(requests, answers, strict=True))
        return self._compiler.compile(rules, connections, resolved)

    async def apply(self, rules: list[RoutingRule]) -> RoutePilotPlan:
        """Builds the plan for ``rules`` and converges the kernel to it."""
        plan = await self.build_plan(rules)
        self._reconciliation.apply_plan(plan)
        return plan
