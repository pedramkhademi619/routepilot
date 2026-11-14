"""NetworkManager D-Bus discovery adapter implementing NetworkDiscoveryPort."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from dbus_fast import BusType
from dbus_fast.aio import MessageBus
from pyroute2 import IPRoute, RawIPRoute

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort

logger = logging.getLogger(__name__)


class NetworkManagerDiscoveryAdapter(NetworkDiscoveryPort):
    """Discovers Linux network connections and routes via NetworkManager D-Bus and Netlink."""

    NM_BUS_NAME = "org.freedesktop.NetworkManager"
    NM_OBJECT_PATH = "/org/freedesktop/NetworkManager"
    NM_IFACE_ACTIVE = "org.freedesktop.NetworkManager.Connection.Active"
    NM_IFACE_DEVICE = "org.freedesktop.NetworkManager.Device"
    NM_IFACE_IP4 = "org.freedesktop.NetworkManager.IP4Config"
    NM_IFACE_PROPS = "org.freedesktop.DBus.Properties"

    def __init__(self) -> None:
        self._bus: MessageBus | None = None
        self._change_callbacks: list[Callable[[list[NetworkConnection]], None]] = []

    async def _get_bus(self) -> MessageBus:
        if self._bus is None or not self._bus.connected:
            self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        return self._bus

    async def discover_connections(self) -> list[NetworkConnection]:
        """Discovers active NetworkManager connections via System D-Bus."""
        try:
            bus = await self._get_bus()
            introspection = await bus.introspect(self.NM_BUS_NAME, self.NM_OBJECT_PATH)
            nm_proxy = bus.get_proxy_object(self.NM_BUS_NAME, self.NM_OBJECT_PATH, introspection)
            props: Any = nm_proxy.get_interface(self.NM_IFACE_PROPS)

            active_paths_variant = await props.call_get(self.NM_BUS_NAME, "ActiveConnections")
            active_paths: list[str] = active_paths_variant.value

            results: list[NetworkConnection] = []
            for path in active_paths:
                conn = await self._inspect_active_connection(bus, path)
                if conn:
                    results.append(conn)

            return results
        except Exception as e:
            logger.warning("NetworkManager D-Bus discovery error: %s. Using Netlink fallback.", e)
            return self._discover_via_netlink_fallback()

    async def get_active_routes(self) -> list[RouteEntry]:
        """Queries the kernel main routing table using pyroute2 RawIPRoute."""
        return await asyncio.to_thread(self._sync_get_active_routes)

    def _sync_get_active_routes(self) -> list[RouteEntry]:
        routes: list[RouteEntry] = []
        try:
            ip = RawIPRoute()
            raw_routes = ip.get_routes(table=254)
            for r in raw_routes:
                attrs = dict(r["attrs"])
                dst = attrs.get("RTA_DST", "0.0.0.0")
                dst_len = r["dst_len"]
                gw = attrs.get("RTA_GATEWAY")
                oif = attrs.get("RTA_OIF")
                metric = attrs.get("RTA_PRIORITY", 100)

                ifname = "unknown"
                if oif:
                    links = ip.get_links(oif)
                    if links:
                        ifname = dict(links[0]["attrs"]).get("IFLA_IFNAME", "unknown")

                routes.append(
                    RouteEntry(
                        destination=f"{dst}/{dst_len}",
                        gateway=gw,
                        interface=ifname,
                        metric=metric,
                        table_id=254,
                        family=r["family"],
                    )
                )
            ip.close()
        except Exception as e:
            logger.error("Failed to read Netlink routes: %s", e)
        return routes

    def subscribe_connection_changes(
        self, callback: Callable[[list[NetworkConnection]], None]
    ) -> None:
        self._change_callbacks.append(callback)

    async def _inspect_active_connection(
        self, bus: MessageBus, path: str
    ) -> NetworkConnection | None:
        try:
            intro = await bus.introspect(self.NM_BUS_NAME, path)
            proxy = bus.get_proxy_object(self.NM_BUS_NAME, path, intro)
            props: Any = proxy.get_interface(self.NM_IFACE_PROPS)

            id_val = (await props.call_get(self.NM_IFACE_ACTIVE, "Id")).value
            uuid_val = (await props.call_get(self.NM_IFACE_ACTIVE, "Uuid")).value
            type_val = (await props.call_get(self.NM_IFACE_ACTIVE, "Type")).value
            vpn_val = bool((await props.call_get(self.NM_IFACE_ACTIVE, "Vpn")).value)
            default_val = bool((await props.call_get(self.NM_IFACE_ACTIVE, "Default")).value)
            default6_val = bool((await props.call_get(self.NM_IFACE_ACTIVE, "Default6")).value)
            devices_val = (await props.call_get(self.NM_IFACE_ACTIVE, "Devices")).value
            ip4_path = (await props.call_get(self.NM_IFACE_ACTIVE, "Ip4Config")).value

            ifname = "unknown"
            if devices_val:
                dev_path = devices_val[0]
                dev_intro = await bus.introspect(self.NM_BUS_NAME, dev_path)
                dev_proxy = bus.get_proxy_object(self.NM_BUS_NAME, dev_path, dev_intro)
                dev_props: Any = dev_proxy.get_interface(self.NM_IFACE_PROPS)
                ifname = (await dev_props.call_get(self.NM_IFACE_DEVICE, "Interface")).value

            ip4_config: IPConfig | None = None
            if ip4_path and ip4_path != "/":
                ip4_config = await self._inspect_ip4_config(bus, ip4_path)

            kind = self._map_connection_type(type_val, vpn_val)

            return NetworkConnection(
                id=str(id_val),
                uuid=str(uuid_val),
                interface=ifname,
                kind=kind,
                is_vpn=vpn_val,
                is_default=default_val,
                is_default6=default6_val,
                state=ConnectionState.ACTIVATED,
                ip4_config=ip4_config,
            )
        except Exception as e:
            logger.debug("Failed to inspect active connection %s: %s", path, e)
            return None

    async def _inspect_ip4_config(self, bus: MessageBus, ip4_path: str) -> IPConfig | None:
        try:
            intro = await bus.introspect(self.NM_BUS_NAME, ip4_path)
            proxy = bus.get_proxy_object(self.NM_BUS_NAME, ip4_path, intro)
            props: Any = proxy.get_interface(self.NM_IFACE_PROPS)

            gw = (await props.call_get(self.NM_IFACE_IP4, "Gateway")).value
            addr_data = (await props.call_get(self.NM_IFACE_IP4, "AddressData")).value

            addresses: list[str] = []
            for ad in addr_data:
                addr = ad.get("address")
                prefix = ad.get("prefix")
                if addr and prefix:
                    addresses.append(f"{addr.value}/{prefix.value}")

            return IPConfig(
                addresses=addresses,
                gateway=str(gw) if gw else None,
            )
        except Exception:
            return None

    def _map_connection_type(self, type_str: str, is_vpn: bool) -> ConnectionKind:
        if is_vpn:
            if "wireguard" in type_str.lower():
                return ConnectionKind.VPN_WIREGUARD
            elif "openvpn" in type_str.lower():
                return ConnectionKind.VPN_OPENVPN
            return ConnectionKind.VPN_GENERIC
        if type_str == "802-11-wireless":
            return ConnectionKind.PHYSICAL_WIFI
        elif type_str == "802-3-ethernet":
            return ConnectionKind.PHYSICAL_ETHERNET
        elif type_str == "bridge":
            return ConnectionKind.BRIDGE
        elif type_str == "loopback":
            return ConnectionKind.LOOPBACK
        elif type_str == "tun":
            return ConnectionKind.TUN
        return ConnectionKind.UNKNOWN

    def _discover_via_netlink_fallback(self) -> list[NetworkConnection]:
        """Fallback discovery directly querying Linux netlink links."""
        results: list[NetworkConnection] = []
        try:
            ip = IPRoute()
            links = ip.get_links()
            for link in links:
                attrs = dict(link["attrs"])
                ifname = attrs.get("IFLA_IFNAME", "unknown")
                operstate = attrs.get("IFLA_OPERSTATE", "UNKNOWN")
                state = (
                    ConnectionState.ACTIVATED if operstate == "UP" else ConnectionState.DISCONNECTED
                )
                is_vpn = ifname.startswith(("vpn", "tun", "wg"))
                kind = ConnectionKind.VPN_GENERIC if is_vpn else ConnectionKind.PHYSICAL_ETHERNET

                results.append(
                    NetworkConnection(
                        id=ifname,
                        uuid=f"netlink-{ifname}",
                        interface=ifname,
                        kind=kind,
                        is_vpn=is_vpn,
                        state=state,
                    )
                )
            ip.close()
        except Exception:
            pass
        return results
