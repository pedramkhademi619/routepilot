# ADR 0001: Native Linux Policy Routing & nftables vs Userspace Proxy Core

## Status
Accepted

## Context
RoutePilot requires a mechanism to selectively steer Linux desktop traffic across multiple network egresses (e.g. physical Wi-Fi/Ethernet vs active VPNs). Two primary design paths were evaluated:
1. Native Linux policy routing (RPDB) via `ip rule`, dedicated routing tables, and `nftables` packet marking.
2. Userspace proxy/routing core (e.g. sing-box, Xray, or Clash) operating via a virtual TUN interface with gVisor.

## Decision
Adopt **Native Linux Policy Routing and nftables** as the primary networking engine. Do not bundle a secondary userspace proxy core.

## Rationale
1. **Performance:** Native kernel routing operates at line-rate in kernel space without userspace context switches, packet memory copying, or TUN latency overhead.
2. **Minimal Footprint:** Native tools rely on existing system facilities (`nftables`, `iproute2`, `systemd-resolved`) already present in modern Linux distributions (Ubuntu, Debian, Fedora, Arch). It does not require distributing a 35MB+ Go binary.
3. **No VPN Contention:** When users already have active WireGuard, OpenVPN, or Cisco AnyConnect connections, running an additional TUN proxy creates routing loops and MTU issues. Native policy routing controls existing interfaces directly.
4. **Licensing Simplicity:** Avoids complex GPL/MPL/Apache dependency licensing interactions with proxy core runtimes.

## Consequences
- Requires root privileges / `CAP_NET_ADMIN`; the GUI never runs as root and asks polkit
  (`pkexec`) to run the one-shot `routepilot apply` command instead.
- Domain routing requires DNS-to-IP resolution sets, with documented CDN/Anycast limitations.
- The concrete table/rule layout is described in [ADR 0006](0006-destination-override-tables.md).
