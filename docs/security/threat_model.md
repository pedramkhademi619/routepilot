# RoutePilot: Security Architecture and Threat Model

**Author:** RoutePilot Security Engineering  
**Revision:** 1.0 (Phase 0)  
**Classification:** Public Security Specification  

---

## 1. System Architecture & Privilege Separation

Running desktop networking tools as `root` is a critical security vulnerability. RoutePilot enforces strict privilege separation between the user interface and system mutation services.

```
+-------------------------------------------------------------+
|                 Unprivileged Desktop (UID 1000)             |
|                                                             |
|   +---------------------+        +----------------------+   |
|   |  PyQt6 Desktop GUI  | <----> |  RoutePilot Core CLI |   |
|   +---------------------+        +----------------------+   |
|              |                                              |
|              v (Structured IPC Request)                     |
+-------------------------------------------------------------+
               |  Unix Domain Socket (/run/routepilot/ipc.sock)
               |  Authenticated via SO_PEERCRED & Polkit
+-------------------------------------------------------------+
|                 Privileged Service (UID 0 / CAP_NET_ADMIN)  |
|                                                             |
|   +-----------------------------------------------------+   |
|   |             routepilot-serviced Daemon              |   |
|   |                                                     |   |
|   |   - Schema & Range Validation                       |   |
|   |   - Atomic Plan Compiler                            |   |
|   |   - Transaction Journal & Automatic Rollback        |   |
|   |   - Isolated nftables: `table inet routepilot`      |   |
|   |   - Policy Routing Tables: `table 10001..10099`     |   |
|   +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

### 1.1 Unprivileged User Tier
- The PyQt6 graphical interface, system tray, configuration viewmodels, and desktop presentation run strictly within the desktop user's unprivileged session.
- The UI never invokes `sudo` or `pkexec` directly on arbitrary bash scripts.
- The UI communicates with the privileged service via an authenticated Unix Domain Socket or system D-Bus.

### 1.2 Privileged Service Tier (`routepilot-serviced`)
- Runs as a systemd service (`routepilot.service`) with bounded capabilities (`CAP_NET_ADMIN`, `CAP_NET_RAW`).
- Validates all incoming IPC payloads using strict schemas before performing any kernel mutation.
- Enforces Polkit authorization (`org.routepilot.policy.apply`) for unprivileged callers.
- Only mutates its own designated resources:
  - Netfilter: Exclusively creates, updates, and deletes `table inet routepilot`. Never touches or flushes existing tables (`table inet filter`, `table inet ufw`, etc.).
  - Routing Tables: Exclusively uses routing table IDs in the reserved range `10001`–`10099`.
  - Routing Rules: Exclusively uses ip rule priorities in range `10000`–`10099`.
  - Marks: Allocates a dedicated bitmask (e.g., `0x00ff0000` or mark values `0x10`–`0x90`).

---

## 2. Threat Analysis & Mitigations

### 2.1 Threat: Command Injection & Arbitrary Shell Execution
- **Risk:** Malicious connection names, domain names, or application paths passed to `subprocess.run(shell=True)`.
- **Mitigation:**
  - `shell=True` is strictly banned across the entire codebase.
  - Netlink operations (routing tables, rules) are performed via binary Netlink sockets using `pyroute2`.
  - Nftables rulesets are compiled in memory and loaded atomically via standard input to `nft -f -` with strict parameter validation.
  - Pydantic models validate all inputs against strict regexes (valid IPv4/IPv6 CIDRs, RFC 1123 domain names, systemd unit name constraints).

### 2.2 Threat: Accidental Routing Loops & VPN Transport Breakage
- **Risk:** If RoutePilot routes all traffic destined for a VPN server IP through that same VPN, an infinite routing loop occurs and the connection collapses.
- **Mitigation:**
  - RoutePilot automatically queries NetworkManager for the VPN gateway/server endpoint IP (e.g. `203.0.113.50`).
  - Explicit high-priority bypass routes are automatically pinned to the physical underlay interface for all active VPN server endpoints.

### 2.3 Threat: VPN Kill-Switch Evasion & Leakage
- **Risk:** If a VPN disconnects, traffic intended for that VPN might silently spill out onto unencrypted public Wi-Fi.
- **Mitigation:**
  - RoutePilot implements **Fail-Closed** as the default action.
  - In nftables, rules destined for an offline VPN interface jump to a `reject` or `drop` verdict chain.
  - Rollback mechanisms ensure that if a routing transaction fails or crashes mid-flight, fail-closed rules remain active until cleanly resolved.

### 2.4 Threat: Service Crash or Desynchronization
- **Risk:** Daemon or GUI crashes leaving orphaned routes or broken connectivity.
- **Mitigation:**
  - **Transaction Journal:** Every state change writes an intent record to `/run/routepilot/journal.json` prior to execution.
  - **Reconciliation on Startup:** When `routepilot-serviced` starts, it reads the journal, inspects live kernel state, and reconciles or resets orphaned `routepilot` resources.
  - **Emergency Recovery CLI:** A standalone recovery tool (`routepilot-recover`) can be executed at any time to purge all RoutePilot tables and rules without affecting other system configurations.

---

## 3. Polkit Action Definition

File: `/usr/share/polkit-1/actions/org.routepilot.policy.policy`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <vendor>RoutePilot Project</vendor>
  <vendor_url>https://github.com/routepilot/routepilot</vendor_url>

  <action id="org.routepilot.policy.apply">
    <description>Apply network routing policies</description>
    <message>Authentication is required to apply RoutePilot traffic routing rules</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
  </action>

  <action id="org.routepilot.policy.recover">
    <description>Emergency reset of RoutePilot routing state</description>
    <message>Authentication is required to reset RoutePilot routing state</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
  </action>
</policyconfig>
```
