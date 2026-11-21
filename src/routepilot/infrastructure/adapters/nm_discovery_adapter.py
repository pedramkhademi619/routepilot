"""NetworkManager D-Bus discovery adapter implementing NetworkDiscoveryPort."""

import asyncio
import ipaddress
import logging
from collections.abc import Callable
from typing import Any

from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus
from pyroute2 import IPRoute

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.connection_state import ConnectionState
from routepilot.domain.models.ip_config import IPConfig
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.ports.network_discovery_port import NetworkDiscoveryPort

logger = logging.getLogger(__name__)

_NM_TYPES = {
    "802-11-wireless": ConnectionKind.PHYSICAL_WIFI,
    "802-3-ethernet": ConnectionKind.PHYSICAL_ETHERNET,
    "wireguard": ConnectionKind.VPN_WIREGUARD,
    "tun": ConnectionKind.TUN,
    "bridge": ConnectionKind.BRIDGE,
    "loopback": ConnectionKind.LOOPBACK,
}
_VPN_TYPES = {"vpn", "wireguard", "tun"}
_NM_STATES = {
    1: ConnectionState.ACTIVATING,
    2: ConnectionState.ACTIVATED,
    3: ConnectionState.DEACTIVATING,
    4: ConnectionState.DEACTIVATED,
}
_TUNNEL_PREFIXES = ("tun", "tap", "wg", "vpn", "ppp", "tailscale", "utun", "sing", "nekoray")


class NetworkManagerDiscoveryAdapter(NetworkDiscoveryPort):
    """Discovers connections via NetworkManager D-Bus, falling back to plain Netlink."""

    NM_BUS_NAME = "org.freedesktop.NetworkManager"
    NM_OBJECT_PATH = "/org/freedesktop/NetworkManager"
    NM_IFACE = "org.freedesktop.NetworkManager"
    NM_IFACE_ACTIVE = "org.freedesktop.NetworkManager.Connection.Active"
    NM_IFACE_DEVICE = "org.freedesktop.NetworkManager.Device"
    NM_IFACE_IP4 = "org.freedesktop.NetworkManager.IP4Config"
    NM_IFACE_IP6 = "org.freedesktop.NetworkManager.IP6Config"

    def __init__(self) -> None:
        self._change_callbacks: list[Callable[[list[NetworkConnection]], None]] = []

    async def discover_connections(self) -> list[NetworkConnection]:
        """Discovers active NetworkManager connections via the system D-Bus."""
        bus: MessageBus | None = None
        try:
            # A short-lived connection per scan keeps the adapter usable from any event loop.
            bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            nm = await self._get_all(bus, self.NM_OBJECT_PATH, self.NM_IFACE)
            results = []
            for path in nm.get("ActiveConnections", []):
                conn = await self._inspect_active_connection(bus, path)
                if conn and conn.kind != ConnectionKind.LOOPBACK:
                    results.append(conn)
            return results
        except Exception as e:
            logger.warning("NetworkManager D-Bus discovery error: %s. Using Netlink fallback.", e)
            return await asyncio.to_thread(self._discover_via_netlink)
        finally:
            if bus is not None:
                bus.disconnect()

    async def get_active_routes(self) -> list[RouteEntry]:
        """Queries the kernel main routing table."""
        return await asyncio.to_thread(self._main_table_routes)

    def subscribe_connection_changes(
        self, callback: Callable[[list[NetworkConnection]], None]
    ) -> None:
        self._change_callbacks.append(callback)

    async def _inspect_active_connection(
        self, bus: MessageBus, path: str
    ) -> NetworkConnection | None:
        try:
            props = await self._get_all(bus, path, self.NM_IFACE_ACTIVE)
            nm_type = str(props.get("Type", ""))
            is_vpn = bool(props.get("Vpn")) or nm_type in _VPN_TYPES

            ip4 = await self._ip_config(bus, props.get("Ip4Config"), self.NM_IFACE_IP4)
            ip6 = await self._ip_config(bus, props.get("Ip6Config"), self.NM_IFACE_IP6)

            interface = "unknown"
            devices = props.get("Devices") or []
            if devices:
                device = await self._get_all(bus, devices[0], self.NM_IFACE_DEVICE)
                interface = str(device.get("IpInterface") or device.get("Interface") or interface)
            if props.get("Vpn") and ip4 and ip4.addresses:
                # Plugin VPNs (OpenVPN, ...) report the parent device; find the tunnel itself.
                interface = await asyncio.to_thread(
                    self._interface_holding, ip4.addresses[0], interface
                )

            kind = _NM_TYPES.get(nm_type, ConnectionKind.VPN_GENERIC if is_vpn else None)
            return NetworkConnection(
                id=str(props.get("Id", interface)),
                uuid=str(props.get("Uuid", path)),
                interface=interface,
                kind=kind or ConnectionKind.UNKNOWN,
                is_vpn=is_vpn,
                is_default=bool(props.get("Default")),
                is_default6=bool(props.get("Default6")),
                state=_NM_STATES.get(int(props.get("State", 2)), ConnectionState.ACTIVATED),
                ip4_config=ip4,
                ip6_config=ip6,
                metric=(ip4.default_route_metric if ip4 else None) or 100,
            )
        except Exception as e:
            logger.debug("Failed to inspect active connection %s: %s", path, e)
            return None

    async def _ip_config(self, bus: MessageBus, path: Any, interface: str) -> IPConfig | None:
        if not path or path == "/":
            return None
        try:
            props = await self._get_all(bus, str(path), interface)
        except Exception:
            return None
        addresses = [
            f"{a['address'].value}/{a['prefix'].value}"
            for a in props.get("AddressData", [])
            if "address" in a and "prefix" in a
        ]
        dns = [str(d["address"].value) for d in props.get("NameserverData", []) if "address" in d]
        routes = [
            {k: v.value for k, v in r.items()}
            for r in props.get("RouteData", [])
            if isinstance(r, dict)
        ]
        return IPConfig(
            addresses=addresses,
            gateway=str(props.get("Gateway")) if props.get("Gateway") else None,
            dns_servers=dns,
            domains=[str(d) for d in props.get("Domains", [])],
            default_route_metric=next(
                (int(r["metric"]) for r in routes if r.get("prefix") == 0 and "metric" in r), None
            ),
        )

    async def _get_all(self, bus: MessageBus, path: str, interface: str) -> dict[str, Any]:
        """Properties.GetAll without introspection round-trips."""
        reply = await bus.call(
            Message(
                destination=self.NM_BUS_NAME,
                path=path,
                interface="org.freedesktop.DBus.Properties",
                member="GetAll",
                signature="s",
                body=[interface],
            )
        )
        if reply is None or reply.message_type == MessageType.ERROR:
            detail = reply.body if reply else "no reply"
            raise RuntimeError(f"GetAll {interface} on {path} failed: {detail}")
        return {key: variant.value for key, variant in reply.body[0].items()}

    @staticmethod
    def _interface_holding(address_cidr: str, default: str) -> str:
        address = address_cidr.split("/")[0]
        with IPRoute() as ip:
            for msg in ip.get_addr(address=address):
                links = ip.get_links(msg["index"])
                if links:
                    return str(links[0].get_attr("IFLA_IFNAME"))
        return default

    def _main_table_routes(self) -> list[RouteEntry]:
        routes: list[RouteEntry] = []
        try:
            with IPRoute() as ip:
                names = {link["index"]: link.get_attr("IFLA_IFNAME") for link in ip.get_links()}
                for family, default in ((2, "0.0.0.0"), (10, "::")):
                    for msg in ip.get_routes(family=family, table=254):
                        routes.append(
                            RouteEntry(
                                destination=f"{msg.get_attr('RTA_DST') or default}/{msg['dst_len']}",
                                gateway=msg.get_attr("RTA_GATEWAY"),
                                interface=names.get(msg.get_attr("RTA_OIF")),
                                metric=msg.get_attr("RTA_PRIORITY") or 0,
                                table_id=254,
                            )
                        )
        except Exception as e:
            logger.error("Failed to read Netlink routes: %s", e)
        return routes

    def _discover_via_netlink(self) -> list[NetworkConnection]:
        """Fallback for systems without NetworkManager (e.g. systemd-networkd)."""
        results: list[NetworkConnection] = []
        try:
            with IPRoute() as ip:
                addresses: dict[int, list[str]] = {}
                for msg in ip.get_addr():
                    addr = msg.get_attr("IFA_ADDRESS")
                    if addr and not ipaddress.ip_address(addr).is_link_local:
                        addresses.setdefault(msg["index"], []).append(f"{addr}/{msg['prefixlen']}")
                gateways: dict[int, tuple[str, int]] = {}
                for msg in ip.get_routes(family=2, table=254):
                    if msg["dst_len"] == 0 and msg.get_attr("RTA_GATEWAY"):
                        metric = msg.get_attr("RTA_PRIORITY") or 0
                        gateways[msg.get_attr("RTA_OIF")] = (msg.get_attr("RTA_GATEWAY"), metric)

                for link in ip.get_links():
                    name = str(link.get_attr("IFLA_IFNAME"))
                    if name == "lo":
                        continue
                    info = link.get_attr("IFLA_LINKINFO")
                    link_kind = info.get_attr("IFLA_INFO_KIND") if info else None
                    is_vpn = link_kind in ("wireguard", "tun") or name.startswith(_TUNNEL_PREFIXES)
                    gateway, metric = gateways.get(link["index"], (None, 100))
                    v4 = [a for a in addresses.get(link["index"], []) if ":" not in a]
                    results.append(
                        NetworkConnection(
                            id=name,
                            uuid=f"netlink-{name}",
                            interface=name,
                            kind=self._guess_kind(name, link_kind, is_vpn),
                            is_vpn=is_vpn,
                            is_default=link["index"] in gateways,
                            state=(
                                ConnectionState.ACTIVATED
                                if link.get_attr("IFLA_OPERSTATE") in ("UP", "UNKNOWN")
                                else ConnectionState.DISCONNECTED
                            ),
                            ip4_config=IPConfig(addresses=v4, gateway=gateway) if v4 else None,
                            metric=metric,
                        )
                    )
        except Exception as e:
            logger.error("Netlink discovery failed: %s", e)
        return results

    @staticmethod
    def _guess_kind(name: str, link_kind: str | None, is_vpn: bool) -> ConnectionKind:
        if link_kind == "wireguard":
            return ConnectionKind.VPN_WIREGUARD
        if is_vpn:
            return ConnectionKind.TUN if link_kind == "tun" else ConnectionKind.VPN_GENERIC
        if link_kind == "bridge":
            return ConnectionKind.BRIDGE
        if name.startswith("wl"):
            return ConnectionKind.PHYSICAL_WIFI
        if name.startswith(("en", "eth")):
            return ConnectionKind.PHYSICAL_ETHERNET
        return ConnectionKind.VIRTUAL if link_kind else ConnectionKind.UNKNOWN
