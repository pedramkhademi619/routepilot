"""Linux kernel RPDB and routing table adapter using pyroute2 Netlink."""

import errno
import logging
import socket
from typing import Any

from pyroute2 import IPRoute
from pyroute2.netlink.exceptions import NetlinkError

from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.models.route_type import RouteType
from routepilot.domain.models.rpdb_rule import RpdbRule
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

logger = logging.getLogger(__name__)

# Kernel route type numbers (rtnetlink.h) <-> RouteType
_RTN_BY_TYPE = {RouteType.UNICAST: 1, RouteType.UNREACHABLE: 7, RouteType.THROW: 9}
_TYPE_BY_RTN = {v: k for k, v in _RTN_BY_TYPE.items()}
# "Nothing to delete" answers from the kernel
_MISSING = (errno.ENOENT, errno.ESRCH)


class Pyroute2RoutingAdapter(PolicyRoutingPort):
    """Adapter executing netlink route and policy rule operations via pyroute2."""

    def replace_route(self, route: RouteEntry) -> None:
        with IPRoute() as ip:
            request = self._route_request(ip, route)
            if route.route_type == RouteType.UNICAST:
                if route.gateway:
                    request["gateway"] = route.gateway
                if route.interface:
                    links = ip.link_lookup(ifname=route.interface)
                    if not links:
                        raise RuntimeError(f"Interface '{route.interface}' does not exist")
                    request["oif"] = links[0]
            ip.route("replace", **request)
        logger.info(
            "Route set: table %d %s %s via %s dev %s",
            route.table_id,
            route.route_type.value,
            route.destination,
            route.gateway,
            route.interface,
        )

    def delete_route(self, route: RouteEntry) -> None:
        with IPRoute() as ip:
            try:
                ip.route("del", **self._route_request(ip, route))
                logger.info("Route removed: table %d %s", route.table_id, route.destination)
            except NetlinkError as e:
                if e.code not in _MISSING:
                    raise

    def list_routes(self, table_id: int, family: int = 4) -> list[RouteEntry]:
        entries: list[RouteEntry] = []
        with IPRoute() as ip:
            for msg in ip.get_routes(family=self._af(family), table=table_id):
                if msg.get_attr("RTA_TABLE") not in (None, table_id):
                    continue
                route_type = _TYPE_BY_RTN.get(msg["type"])
                if route_type is None:
                    continue  # e.g. local/broadcast routes we never create
                default_dst = "0.0.0.0" if family == 4 else "::"
                dst = msg.get_attr("RTA_DST") or default_dst
                oif = msg.get_attr("RTA_OIF")
                entries.append(
                    RouteEntry(
                        destination=f"{dst}/{msg['dst_len']}",
                        gateway=msg.get_attr("RTA_GATEWAY"),
                        interface=self._ifname(ip, oif) if oif else None,
                        metric=msg.get_attr("RTA_PRIORITY") or 0,
                        table_id=table_id,
                        route_type=route_type,
                    )
                )
        return entries

    def flush_table(self, table_id: int, family: int = 4) -> None:
        for route in self.list_routes(table_id, family):
            self.delete_route(route)
        logger.info("Flushed table %d (IPv%d)", table_id, family)

    def replace_rule(self, rule: RpdbRule) -> None:
        with IPRoute() as ip:
            existing = [
                r
                for r in ip.get_rules(family=self._af(rule.family))
                if r.get_attr("FRA_PRIORITY") == rule.priority
            ]
            if len(existing) == 1 and self._rule_table(existing[0]) == rule.table_id:
                return  # Already in place; avoid a delete/add window
            self._delete_rules_at(ip, rule.priority, rule.family)
            ip.rule(
                "add",
                table=rule.table_id,
                priority=rule.priority,
                family=self._af(rule.family),
            )
        logger.info(
            "ip rule set: prio %d lookup %d (IPv%d)", rule.priority, rule.table_id, rule.family
        )

    def delete_rule(self, priority: int, family: int = 4) -> None:
        with IPRoute() as ip:
            self._delete_rules_at(ip, priority, family)

    def _delete_rules_at(self, ip: IPRoute, priority: int, family: int) -> None:
        # A priority can hold several rules; delete until the kernel reports none left.
        for _ in range(64):
            try:
                ip.rule("del", priority=priority, family=self._af(family))
            except NetlinkError as e:
                if e.code in _MISSING:
                    return
                raise
            logger.info("ip rule removed: prio %d (IPv%d)", priority, family)

    def _route_request(self, ip: IPRoute, route: RouteEntry) -> dict[str, Any]:
        return {
            "dst": route.destination,
            "table": route.table_id,
            "family": self._af(route.family),
            "type": _RTN_BY_TYPE[route.route_type],
        }

    @staticmethod
    def _rule_table(msg: Any) -> int:
        return int(msg.get_attr("FRA_TABLE") or msg["table"])

    @staticmethod
    def _ifname(ip: IPRoute, index: int) -> str | None:
        links = ip.get_links(index)
        return str(links[0].get_attr("IFLA_IFNAME")) if links else None

    @staticmethod
    def _af(family: int) -> int:
        return socket.AF_INET6 if family == 6 else socket.AF_INET
