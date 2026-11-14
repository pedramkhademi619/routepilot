# RoutePilot: Capability Matrix & Honest Technical Boundaries

This document defines the exact capabilities, approximations, conflicts, and unsupported scenarios in RoutePilot. We reject false marketing claims: networking on Linux is bound by kernel state machines and protocol specifications.

---

## 1. Network & VPN Connection Support Matrix

| Connection Type | Support Status | Capabilities & Limitations |
| :--- | :--- | :--- |
| **NetworkManager Managed VPNs** (WireGuard, OpenVPN, StrongSwan, Libreswan) | **Fully Supported** | Full discovery, state event monitoring, UUID tracking, gateway & metric extraction, selective bypass, and exclusive routing. |
| **Standalone WireGuard Interfaces** (`wg-quick`, `systemd-networkd`) | **Supported** | Discovered via Netlink (`pyroute2`). fwmark coexistence requires configuring non-overlapping mark bits (avoiding `0xca6c`). |
| **Standalone OpenVPN** (`tun0` without NM) | **Supported** | Discovered via Netlink. Works if OpenVPN was launched with default route in main table. |
| **Simultaneous Multiple Active VPNs** | **Supported** | Destination IP ranges or applications can be pinned to VPN A or VPN B via distinct policy routing tables. |
| **VPN Chaining** (VPN A through VPN B) | **Unsupported** | RoutePilot does not implement recursive encapsulation (tunnels inside tunnels). Multi-VPN support means *parallel selection*, not chaining. |
| **Commercial 3rd-Party VPN Clients** (with proprietary firewall kill-switches) | **Conflicting / Advisory** | Many commercial clients (e.g. Mullvad, Proton, ExpressVPN) install strict nftables/iptables drop rules (`drop all except vpn_interface`). RoutePilot detects these conflicting drop rules and warns the user rather than invisibly breaking the kill-switch. |
| **Proxy-Only Tools** (Clash, Shadowsocks, V2Ray in SOCKS5/HTTP mode) | **Unsupported** | Tools that do not expose a network link or TUN device cannot be routed via kernel policy routing tables. |

---

## 2. Traffic Selector Capabilities & Limitations

### 2.1 IP Address & CIDR Routing
- **Status:** **Fully Supported (Exact Kernel Match)**
- **Behavior:** Packets destined for the specified IPv4/IPv6 address or CIDR subnet (e.g., `192.168.10.0/24`, `2001:db8::/32`) are matched in nftables sets and routed via the assigned policy table.
- **Parity:** Full IPv4 and IPv6 dual-stack parity.

### 2.2 Domain Name Routing
- **Status:** **Partially Supported (Approximation via DNS-to-IP Set)**
- **Limitations:**
  1. **IP Routing != Domain Routing:** Linux kernel IP routing operates on IP headers, not HTTP/TLS domain names.
  2. **Shared CDN / Anycast Addresses:** If `example.com` is hosted on Cloudflare, Akamai, or AWS CloudFront, its IP address is shared with hundreds of thousands of unrelated domains. Bypassing `example.com` automatically bypasses all other traffic heading to that shared edge IP.
  3. **DNS Dynamic Changes & TTL:** Domain IP mappings change. RoutePilot periodically re-resolves domain names and monitors system resolver state, but cached sockets may use older IPs.
  4. **Encrypted DNS (DoH / DoT):** Modern web browsers (Firefox, Chrome) often enable DNS-over-HTTPS by default, bypassing `systemd-resolved`. When DoH is active, the browser's resolved IP may diverge from RoutePilot's resolved IP set. RoutePilot displays a clear UI alert explaining how to configure browser DNS for consistent split-tunneling.
  5. **URL Paths:** Paths (`example.com/api`) *cannot* be routed via network policy routing. The UI strips paths and warns the user if a full URL is entered.

### 2.3 Application-Level Routing
- **Status:** **Supported via cgroup v2 Managed Launch; Unmanaged Running Apps Unsupported**
- **Capabilities:**
  - Applications launched via RoutePilot are placed into an isolated systemd cgroup v2 scope (`routepilot-app-<id>.scope`).
  - All subprocesses, threads, and child processes inherit this cgroup automatically.
  - nftables matches `socket cgroupv2` and marks all outbound packets deterministically.
- **Limitations:**
  - **Existing Open Sockets:** An already-running application cannot have its existing TCP connections moved to a different network interface on the fly without breaking the TCP connection, because TCP sockets are permanently bound to `(source_ip, source_port)`. Application restart is required.
  - **Flatpak & Snap:** Flatpak and Snap applications run inside their own sandboxes and systemd scopes. RoutePilot provides launch wrappers that integrate with Flatpak (`flatpak run --command=...`).
  - **Helper Daemons & D-Bus Activation:** If an application delegates network traffic to a background system daemon (e.g., `geoclue`, systemd-resolved, or a shared service), that traffic originates from the daemon's cgroup, not the application's scope.

---

## 3. Policy Semantics: Distinguishing Actions & Fallbacks

RoutePilot enforces a strict typed policy model to prevent security illusions:

1. **"Not using VPN A" != "Using VPN B":**
   Excluding a VPN means the traffic is ineligible for VPN A. It does not blindly assign it to VPN B unless explicitly configured.
2. **Explicit Egress ("Direct Internet"):**
   "Direct Internet" is strictly defined as an identified physical non-VPN network connection (e.g., `wlo1` or `enp45s0`), *never* the main routing table (which may itself be hijacked by a VPN default route).
3. **Fail-Closed vs Fail-Open:**
   - **Fail-Closed (Default):** If a required VPN or direct connection is disconnected or unavailable, traffic matching the rule is dropped (`blackhole` or `reject`). It *never* silently leaks onto default internet.
   - **Fail-Open (Optional, requires explicit user consent):** Falls back to system default routing only if the user explicitly checked the risk acknowledgement.
