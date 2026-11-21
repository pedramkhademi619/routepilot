# RoutePilot: Capability Matrix & Honest Technical Boundaries

What RoutePilot does today, what it approximates, and what it cannot do. Networking on Linux is
bound by kernel semantics; this page avoids marketing claims on purpose.

---

## 1. Connections & VPN clients

| Setup | Status | Notes |
| :-- | :-- | :-- |
| NetworkManager links (Wi-Fi, Ethernet) | **Supported** | Discovered over D-Bus with gateways, metrics and IPv6. Used as the "direct" egress. |
| NetworkManager VPNs (OpenVPN, WireGuard, IPsec plugins, `tun`) | **Supported** | Detected as VPNs; tunnel interface found from the VPN's address for plugin VPNs. |
| TUN-mode clients (sing-box, clash/mihomo, v2ray/xray front-ends, Hiddify…) | **Supported** | RoutePilot's rules (prio 4810/4820) run before their `9000+` rules. Clients that intercept traffic with their own nftables redirect (e.g. sing-box `auto_redirect`) can still capture it. |
| wg-quick / systemd-networkd WireGuard | **Supported** | Works alongside the `0xca6c` fwmark rules; RoutePilot uses no packet marks. |
| Systems without NetworkManager | **Basic** | Netlink fallback discovers links, addresses and default gateways. |
| Several VPNs at once | **Supported** | "VPN only" rules can pin destinations to a specific VPN. |
| VPN chaining (VPN inside VPN) | **Not supported** | Multi-VPN means parallel selection, not nesting. |
| Clients with strict kill-switch firewalls (Mullvad, Proton, …) | **Conflicting** | Their drop rules also drop RoutePilot's bypass traffic. Use the client's own split tunneling. |
| SOCKS/HTTP-proxy-only tools | **Not applicable** | No interface to route through. |

---

## 2. Selectors

### IP addresses and CIDR ranges — exact
Matched by the kernel per packet, IPv4 and IPv6. Overlapping ranges follow longest-prefix
match; identical destinations are decided by rule priority.

### Domains — approximation
* Routing works on IP addresses. RoutePilot resolves the domain (and `www.` for
  "domain and subdomains") **through the DNS servers of the link the traffic will use** and
  routes those addresses. Arbitrary subdomains cannot be enumerated — add rules for the ones you
  need, or use a CIDR rule if the service publishes its ranges.
* `~domain` routing domains are added to that link in systemd-resolved so applications resolve
  the same addresses RoutePilot routed.
* Shared CDN / anycast addresses are shared by many sites; routing one affects the others.
* Addresses change. Domains are re-resolved every time you apply (any rule change applies);
  periodic re-resolution is planned.
* Browsers with their own DNS-over-HTTPS can resolve different addresses than the system.
* URLs are reduced to their host name; paths cannot be routed.

### Applications — planned
Accepted in the policy format but skipped when applying (see ADR 0004/0006).

---

## 3. Actions & fallbacks

| Action | Kernel effect |
| :-- | :-- |
| Direct (bypass VPN) | route `via <gateway> dev <physical link>` in table 10001 |
| Through VPN only | route `dev <vpn interface>` in table 10001 |
| System default | `throw` route: overrides lower-priority rules for that destination |
| Block | `reject` in `table inet routepilot` (fails fast instead of timing out) |

| If the path is unavailable | Effect |
| :-- | :-- |
| Block it (fail-closed, default) | `unreachable` guard route in table 10002 — also protects when the link drops later |
| Use the normal route (fail-open) | nothing installed; traffic follows the system routing table |

Existing connections keep their path until they reconnect (a TCP socket's source address cannot
change mid-connection).
