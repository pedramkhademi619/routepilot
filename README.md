# RoutePilot

**RoutePilot** is a production-minded Linux desktop utility and system service for selective VPN bypass and traffic policy routing. It empowers Linux desktop users to route traffic by destination IP/CIDR, domain, or application across multiple active network connections and VPNs without compromising system security.

Built primarily in Python with **PyQt6**, **nftables**, **Linux policy routing (RPDB)**, and **NetworkManager D-Bus**.

---

## Key Capabilities

- **Connection & VPN Discovery:** Discovers active NetworkManager connections, VPNs (WireGuard, OpenVPN, Tun), physical links, and default routing metrics.
- **Traffic Policy Engine:**
  - Route destination IP ranges / CIDRs directly to normal internet (bypassing active VPN) or to a selected VPN interface.
  - Domain-level split DNS and dynamic IP routing sets with honest CDN/Anycast warnings.
  - Application-level routing via systemd cgroup v2 managed scopes.
- **Fail-Safe & Isolation:**
  - Dedicated `table inet routepilot` namespace — never touches or flushes `ufw`, `firewalld`, or Docker rules.
  - Fail-closed policies: Block traffic if required VPN drops instead of silently leaking out direct internet.
  - Staged atomic plan application with automatic rollback and journaled recovery.
- **Unprivileged Desktop UI:** The PyQt6 GUI runs strictly as unprivileged user; all privileged operations are mediated via polkit and structured local IPC.

---

## License

GNU General Public License v3.0 or later (`GPL-3.0-or-later`). See [LICENSE](LICENSE) for details.
