"""Unit tests for the apply use case (discovery -> resolution -> compile -> reconcile)."""

from unittest.mock import MagicMock

from factories import rule, vpn, wifi

from routepilot.application.services.policy_apply_service import PolicyApplyService
from routepilot.application.services.reconciliation_service import ReconciliationService
from routepilot.domain.policy.selector_type import SelectorType
from routepilot.domain.ports.dns_resolver_port import DnsResolverPort
from routepilot.infrastructure.adapters.mock_discovery_adapter import MockDiscoveryAdapter


class FakeResolver(DnsResolverPort):
    def __init__(self) -> None:
        self.queries: list[tuple[str, str | None]] = []

    async def resolve_domain(self, domain: str, interface: str | None = None) -> list[str]:
        self.queries.append((domain, interface))
        return {"example.ir": ["203.0.113.7"]}.get(domain, [])

    def configure_split_dns(self, interface, domains, previous=None) -> None:  # type: ignore[no-untyped-def]
        pass

    def reset_split_dns(self, interface, domains) -> None:  # type: ignore[no-untyped-def]
        pass


async def test_apply_resolves_through_target_link_and_reconciles() -> None:
    resolver = FakeResolver()
    reconciliation = MagicMock(spec=ReconciliationService)
    service = PolicyApplyService(MockDiscoveryAdapter([wifi(), vpn()]), resolver, reconciliation)

    plan = await service.apply([rule("Site", "example.ir", selector=SelectorType.DOMAIN)])

    assert resolver.queries == [("example.ir", "wlo1")]
    assert [r.destination for r in plan.routes if r.interface == "wlo1"] == ["203.0.113.7/32"]
    reconciliation.apply_plan.assert_called_once_with(plan)


async def test_build_plan_does_not_touch_the_kernel() -> None:
    reconciliation = MagicMock(spec=ReconciliationService)
    service = PolicyApplyService(MockDiscoveryAdapter([wifi()]), FakeResolver(), reconciliation)

    await service.build_plan([rule("Net", "198.51.100.0/24")])

    reconciliation.apply_plan.assert_not_called()
