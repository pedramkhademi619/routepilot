"""Kernel resources (tables and rule priorities) owned by RoutePilot."""


class RoutingLayout:
    """Single source of truth for the routing tables and ip rule priorities RoutePilot owns.

    Lookups for every packet walk the RPDB in priority order:

    * ``OVERRIDE_PRIORITY`` -> ``OVERRIDE_TABLE``: per-destination routes that pin traffic to
      a chosen egress (direct link or a specific VPN). Destinations without a route here fall
      through untouched.
    * ``GUARD_PRIORITY`` -> ``GUARD_TABLE``: ``unreachable`` routes for fail-closed rules. They
      only match when the override route disappeared (e.g. the target link went down), so
      traffic is refused instead of silently leaking through another path.

    The priorities sit below the ones used by common VPN clients (sing-box/clash ``9000+``,
    wg-quick ``32764``), so overrides keep working whichever client owns the default route.
    """

    OVERRIDE_TABLE = 10001
    GUARD_TABLE = 10002
    OVERRIDE_PRIORITY = 4810
    GUARD_PRIORITY = 4820
    FAMILIES = (4, 6)

    # Resources used by RoutePilot <= 0.1, removed during teardown so upgrades start clean.
    LEGACY_RULE_PRIORITIES = (10010,)

    @classmethod
    def owned_tables(cls) -> tuple[int, int]:
        return (cls.OVERRIDE_TABLE, cls.GUARD_TABLE)

    @classmethod
    def owned_priorities(cls) -> tuple[int, int]:
        return (cls.OVERRIDE_PRIORITY, cls.GUARD_PRIORITY)

    @classmethod
    def priority_for_table(cls, table_id: int) -> int:
        return cls.OVERRIDE_PRIORITY if table_id == cls.OVERRIDE_TABLE else cls.GUARD_PRIORITY
