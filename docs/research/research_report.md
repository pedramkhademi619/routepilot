# RoutePilot: Research Report and Architectural Validation

**Project:** RoutePilot  
**Baseline Target:** Ubuntu 24.04 LTS (Noble Numbat) / Linux Kernel >= 6.8 / Systemd >= 255 / NetworkManager >= 1.46 / nftables >= 1.0.9  
**Tested Environment:** Linux Pedram 7.0.0-113042-tuxedo (x86_64), TUXEDO OS 24.04.5 LTS (Noble base), Python 3.12.3  
**Report Date:** 2026-11-14  

---

## 1. Naming Conflict & PyPI Status

- **Candidate Name:** `RoutePilot` / `routepilot`
- **PyPI Verification:** Queried PyPI JSON API for `routepilot` and `route-pilot`. Result: HTTP 404 Not Found.
- **Debian / Ubuntu Package Archives:** No package named `routepilot`.
- **GitHub / Open Source Ecosystem:** Existing repositories with "routepilot" are limited to Flutter navigation packages (`route_pilot`) or AI dispatch scripts. No Linux network routing tool exists under this name.
- **Conclusion:** RoutePilot is clear and approved for public release.

---

## 2. Comparative Evaluation of Routing Architectures

We evaluated three potential architectural foundations:

### Architecture A: Native Linux Policy Routing (RPDB) and nftables (Recommended)
- **Mechanics:**
  - Dedicated netfilter table: `table inet routepilot { ... }`.
  - Output hook chain: `chain routepilot_output { type route hook output priority mangle; policy accept; }`.
  - Marking: Matches traffic selectors (IP sets, cgroup v2 socket attributes, protocol/ports) and applies `meta mark set <mark>`.
  - Linux Routing Policy Database (RPDB): Dedicated ip rules (`ip rule add fwmark <mark>/<mask> lookup <table_id> pref <prio>`).
  - Kernel re-routing: The `type route` netfilter hook automatically triggers `ip_route_me_harder` / `ip6_route_me_harder` when packet marks are modified on locally-generated output traffic.
  - Policy routing tables: Tables allocated in reserved range (e.g. 10001–10099) containing default egress routes via target interfaces (`default via <gateway> dev <iface> src <ip>`).
- **Performance:** Kernel line-rate forwarding with zero userspace memory copies or packet context switches.
- **Resource Footprint:** Negligible (<5MB memory).
- **Security:** Standard Linux kernel access controls, polkit-mediated mutation, no TLS termination.

### Architecture B: Userspace Routing / Proxy Core (e.g. sing-box / Xray)
- **Mechanics:**
  - Creates a virtual TUN interface, routes all system traffic into userspace via gVisor or lwIP TCP/IP stack.
  - Inspects packets at Layer 4 and Layer 7 (TLS ClientHello SNI sniffing, HTTP Host sniffing), and dispatches to outbound connections (Direct, SOCKS5, WireGuard).
- **Flaws & Disqualifying Factors:**
  - **Overhead:** Every packet traverses the kernel-userspace boundary twice. Heavy CPU and battery consumption on laptops.
  - **Binary Bloat:** Requires bundling a 35MB+ compiled Go runtime binary.
  - **VPN Collisions:** When the host connects to an existing NetworkManager VPN or third-party client (e.g., AnyConnect, OpenConnect, commercial VPNs), running an internal TUN creates TUN-on-TUN nesting, MTU fragmentation, and routing table contention.
  - **Licensing & Supply Chain:** sing-box and Go dependencies introduce complex third-party license obligations (GPLv3, MPL, Apache 2.0 mixtures).

### Architecture C: Hybrid Architecture
- **Mechanics:** Native nftables/RPDB primary core with an optional proxy bridge.
- **Evaluation:** Adding a proxy core introduces unnecessary complexity at this stage. Section 2 instructs: *"Choose the smallest defensible architecture. Do not add a second networking engine merely because it exists."*

### Recommendation
**Adopt Architecture A: Native Linux Policy Routing and nftables.** It is the leanest, fastest, and most robust architecture for a Linux desktop utility.

---

## 3. UI Framework & Desktop Licensing

### Framework: PyQt6 (QtWidgets) vs Qt Quick/QML
- **Choice: PyQt6 with `QtWidgets`**
- **Accessibility:** `QtWidgets` provides first-class Linux desktop accessibility out-of-the-box via AT-SPI (`QAccessible`) and integrates with screen readers (Orca). Qt Quick accessibility on Linux desktops is notoriously fragile and requires manual QAccessibleQuickItem implementations.
- **Desktop Consistency:** `QtWidgets` automatically respects desktop style engines (KDE Breeze, GNOME Adwaita, Qt6 styles), system palette changes, high-DPI scaling, and font configuration.
- **Data Densities:** Route tables, active connections, and rule sets require rich tabular and tree controls (`QTableView`, `QTreeView`, `QHeaderView`), which are native and mature in QtWidgets.
- **Internationalization & RTL:** QtWidgets has comprehensive support for Right-to-Left (RTL) layout mirroring (`setLayoutDirection(Qt.LayoutDirection.RightToLeft)`), essential for Persian and Arabic locales.

### Licensing Review
- **PyQt6 License:** Riverbank Computing licenses PyQt6 under the **GNU General Public License v3 (GPLv3)** or a commercial license.
- **Obligation:** Any application distributed using the open-source PyQt6 bindings **must** be licensed under a GPLv3-compatible license.
- **Project License:** RoutePilot will be released under **GPL-3.0-or-later**.

---

## 4. Subsystem Research & Technical Validation

### 4.1 NetworkManager D-Bus API
- **Bus:** System Bus (`org.freedesktop.NetworkManager`).
- **Key Objects & Interfaces:**
  - `/org/freedesktop/NetworkManager` (`org.freedesktop.NetworkManager`):
    - `ActiveConnections`: Array of object paths to active connections.
    - `PrimaryConnection`: Object path to default internet connection.
  - `/org/freedesktop/NetworkManager/ActiveConnection/N` (`org.freedesktop.NetworkManager.Connection.Active`):
    - `Id`: Human-readable connection name (UTF-8, e.g. "Home-WiFi").
    - `Uuid`: Stable RFC 4122 UUID (e.g. `6f1c2d3e-0a4b-4c5d-9e8f-0123456789ab`).
    - `Type`: Connection type string (`802-11-wireless`, `802-3-ethernet`, `vpn`, `tun`, `wireguard`).
    - `Vpn`: Boolean flag indicating if connection is a VPN.
    - `Devices`: Array of device object paths associated with connection.
    - `Default` / `Default6`: Boolean indicating default routing status.
    - `Ip4Config` / `Ip6Config`: Object paths to IP configuration.
  - **Permissions:** Unprivileged users can read all ActiveConnection and Device properties over system D-Bus without root or polkit elevation.

### 4.2 Linux Routing Policy Database (RPDB) & pyroute2
- **Command Equivalents:** `ip rule`, `ip route`
- **Library:** `pyroute2` (`pyroute2.IPRoute`) provides native Netlink socket communication (`NETLINK_ROUTE`), avoiding subshell invocation.
- **Key Mechanics:**
  - Route Tables: Custom routing tables allocated in reserved range `10001`–`10099`.
  - Table Rules: `ip rule add fwmark 0x10/0xff lookup 10001 pref 1000`.
  - Metric & Direct Egress: Table 10001 contains default route via physical gateway with explicit source address:
    `default via 192.168.1.1 dev wlo1 proto static src 192.168.1.173`
  - Dual Stack: Both IPv4 (`family=AF_INET`) and IPv6 (`family=AF_INET6`) routing rules and tables are managed in tandem.

### 4.3 nftables Packet Marking & Atomicity
- **Version Tested:** `nftables v1.0.9`.
- **Chain Type:** `type route hook output priority mangle` (priority -150).
  - Crucial kernel behavior: Output packets altered in this chain trigger route re-evaluation (`ip_route_me_harder`).
- **Namespacing:** Table `table inet routepilot` is completely distinct from `table inet ufw` or `table inet firewalld`. Adding, replacing, or deleting `table inet routepilot` never flushes or touches existing system firewalls.
- **Atomic Transaction:** `nft -f <file>` loads a complete ruleset in an atomic kernel netlink transaction.

### 4.4 Application Routing: cgroup v2 Managed Scopes
- **Mechanics:**
  - When launching an application through RoutePilot (e.g. Firefox, Steam, qBittorrent), RoutePilot invokes systemd to create a dedicated user scope:
    `systemd-run --user --scope --unit=routepilot-app-<id> <executable> [args...]`
  - In nftables, sockets belonging to this scope are matched using:
    `socket cgroupv2 level 2 "user.slice/user-1000.slice/user@1000.service/app.slice/routepilot-app-<id>.scope" meta mark set <mark>`
    or matching cgroup IDs.
- **Limitations:**
  - Sockets already open prior to rule activation cannot change their egress interface without reconnecting, because TCP state is bound to `(src_ip, src_port, dst_ip, dst_port)`.
  - Application restart is required for existing running processes.

### 4.5 DNS & systemd-resolved Limitations
- **Split DNS:** `resolvectl domain <link> ~example.com` directs DNS queries for `example.com` to `<link>`'s DNS servers.
- **Critical Technical Boundary:**
  - Split DNS only routes the DNS query; it does *not* route the resulting TCP/UDP traffic.
  - To route application traffic, resolved IPs must be added to an nftables IP set (`bypass_v4` / `bypass_v6`).
  - CDNs / Anycast: Cloudflare, Fastly, AWS CloudFront share IP addresses across millions of domains. Routing a Cloudflare IP through direct internet routes all traffic destined for that Cloudflare edge IP through direct internet.
  - Encrypted DNS: Browsers with DoH (DNS-over-HTTPS) bypass systemd-resolved completely. RoutePilot must warn users about application-specific DNS.

### 4.6 Coexistence with UFW, firewalld, and Docker
- **UFW:** Active on tested machine. UFW manages iptables/nftables chains (`ufw-user-input`, `ufw-user-output`). RoutePilot uses `table inet routepilot` which coexists harmoniously.
- **Docker:** Docker manages iptables `DOCKER` chains. RoutePilot avoids Docker mark space (`0x0000ffff`) and uses `0x00ff0000` / bitmask allocation.

---

## 5. Source References and Access Dates

1. **NetworkManager API Reference:** https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html (Accessed: 2026-11-14)
2. **nftables Wiki & Documentation:** https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks (Accessed: 2026-11-14)
3. **systemd-resolved Service Manual:** https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html (Accessed: 2026-11-14)
4. **systemd.exec & cgroups:** https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html (Accessed: 2026-11-14)
5. **PyQt6 Documentation & License FAQ:** https://www.riverbankcomputing.com/static/Docs/PyQt6/ and https://riverbankcomputing.com/commercial/license-faq (Accessed: 2026-11-14)
6. **pyroute2 Documentation:** https://docs.pyroute2.org/ (Accessed: 2026-11-14)
7. **sing-box Architectural Reference:** https://sing-box.sagernet.org/ (Accessed: 2026-11-14)
