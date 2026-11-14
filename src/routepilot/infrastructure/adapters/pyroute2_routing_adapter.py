"""Linux kernel RPDB and routing table adapter using pyroute2 Netlink."""

import logging

from pyroute2 import IPRoute

from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort

logger = logging.getLogger(__name__)


class Pyroute2RoutingAdapter(PolicyRoutingPort):
    """Adapter executing netlink route and policy rule operations via pyroute2."""

    def add_routing_table_route(self, table_id: int, route: RouteEntry) -> None:
        ip = IPRoute()
        try:
            oif = None
            if route.interface and route.interface != "unknown":
                links = ip.link_lookup(ifname=route.interface)
                if links:
                    oif = links[0]

            kwargs = {
                "dst": route.destination if route.destination != "0.0.0.0/0" else "default",
                "table": table_id,
                "metric": route.metric,
            }
            if route.gateway:
                kwargs["gateway"] = route.gateway
            if oif:
                kwargs["oif"] = oif

            ip.route("replace", **kwargs)
            logger.info(
                "Route added: table %d dst %s via %s dev %s",
                table_id,
                route.destination,
                route.gateway,
                route.interface,
            )
        finally:
            ip.close()

    def remove_routing_table_route(self, table_id: int, destination: str, family: int = 4) -> None:
        ip = IPRoute()
        try:
            dst = destination if destination != "0.0.0.0/0" else "default"
            ip.route("del", dst=dst, table=table_id, family=family)
            logger.info("Route removed: table %d dst %s", table_id, destination)
        except Exception as e:
            logger.debug("Route del non-fatal error: %s", e)
        finally:
            ip.close()

    def add_policy_rule(
        self, table_id: int, priority: int, fwmark: int, fwmask: int = 0x00FF0000, family: int = 4
    ) -> None:
        ip = IPRoute()
        try:
            # Delete existing rule at this priority if present to maintain idempotency
            try:
                ip.rule("del", priority=priority, family=family)
            except Exception:
                pass

            ip.rule(
                "add",
                table=table_id,
                priority=priority,
                fwmark=fwmark,
                fwmask=fwmask,
                family=family,
            )
            logger.info(
                "IP rule added: mark %s/%s -> table %d prio %d",
                hex(fwmark),
                hex(fwmask),
                table_id,
                priority,
            )
        finally:
            ip.close()

    def remove_policy_rule(self, priority: int, family: int = 4) -> None:
        ip = IPRoute()
        try:
            ip.rule("del", priority=priority, family=family)
            logger.info("IP rule removed: prio %d", priority)
        except Exception as e:
            logger.debug("IP rule remove non-fatal error: %s", e)
        finally:
            ip.close()

    def flush_table_routes(self, table_id: int, family: int = 4) -> None:
        ip = IPRoute()
        try:
            routes = ip.get_routes(table=table_id, family=family)
            for r in routes:
                attrs = dict(r["attrs"])
                dst = attrs.get("RTA_DST", "default")
                try:
                    ip.route("del", dst=dst, table=table_id, family=family)
                except Exception:
                    pass
            logger.info("Flushed routes in table %d", table_id)
        finally:
            ip.close()

    def list_table_routes(self, table_id: int, family: int = 4) -> list[RouteEntry]:
        ip = IPRoute()
        entries: list[RouteEntry] = []
        try:
            raw_routes = ip.get_routes(table=table_id, family=family)
            for r in raw_routes:
                attrs = dict(r["attrs"])
                dst = attrs.get("RTA_DST", "0.0.0.0")
                dst_len = r["dst_len"]
                gw = attrs.get("RTA_GATEWAY")
                metric = attrs.get("RTA_PRIORITY", 100)
                oif = attrs.get("RTA_OIF")
                ifname = "unknown"
                if oif:
                    links = ip.get_links(oif)
                    if links:
                        ifname = dict(links[0]["attrs"]).get("IFLA_IFNAME", "unknown")
                entries.append(
                    RouteEntry(
                        destination=f"{dst}/{dst_len}",
                        gateway=gw,
                        interface=ifname,
                        metric=metric,
                        table_id=table_id,
                        family=family,
                    )
                )
        finally:
            ip.close()
        return entries
