# RoutePilot: Security Architecture and Threat Model

This document describes how RoutePilot separates privileges, which kernel resources it owns,
and the threats it is designed against. It reflects the code as of version 0.2.

---

## 1. Architecture & Privilege Separation

```
+---------------------------------------------------------------+
|  Desktop session (unprivileged user)                          |
|                                                               |
|   PyQt6 GUI  ──edits──>  ~/.config/routepilot/policy.json     |
|      │                                                        |
|      └─ QProcess: python -m routepilot --policy <file> apply  |
+------│--------------------------------------------------------+
       │  pkexec (polkit authentication dialog, auth_admin)
+------▼--------------------------------------------------------+
|  One-shot privileged process (root, exits when done)          |
|                                                               |
|   PolicyApplyService ─> PlanCompiler ─> ReconciliationService |
|     • discovers links via NetworkManager D-Bus / netlink      |
|     • resolves domains through the target link's DNS          |
|     • writes the plan journal to /run/routepilot (tmpfs)      |
|     • converges only RoutePilot-owned kernel resources        |
+---------------------------------------------------------------+
```

* The GUI never runs as root and never builds shell commands. It starts exactly one program,
  the RoutePilot CLI, with a fixed argument list.
* The privileged CLI re-reads and re-validates the policy file itself; nothing the GUI computed
  is trusted.
* There is no long-running privileged daemon. (A service with signal-driven re-apply on network
  changes is on the roadmap.)

### 1.1 Resources RoutePilot owns (and the only ones it changes)

| Resource | Identifier |
| :-- | :-- |
| ip rules | priorities `4810` (lookup `10001`) and `4820` (lookup `10002`), IPv4 and IPv6 |
| routing tables | `10001` (overrides), `10002` (fail-closed guards) |
| nftables | `table inet routepilot` only — `ufw`, `firewalld`, Docker and other tables are never touched |
| systemd-resolved | `~domain` routing domains it added, on the link it added them to; other link domains are preserved |
| state | `/run/routepilot/journal.json` (root, tmpfs) |

`routepilot reset` removes all of the above. Upgrading from 0.1.x additionally removes the old
priority `10010` rule and the main-table host routes recorded by 0.1.x.

---

## 2. Threats & Mitigations

### 2.1 Command injection
* `shell=True` is never used. External tools (`nft`, `resolvectl`, `pkexec`) receive argument
  lists; nftables rulesets are passed on standard input.
* Routes and rules are programmed through netlink (`pyroute2`), not by invoking `ip`.
* Everything written into a ruleset or route is first parsed by `ipaddress` (CIDRs/addresses);
  domain selectors must match an RFC 1123 hostname pattern.

### 2.2 Traffic leaks when a path disappears
* Fail-closed is the default fallback. For such rules RoutePilot installs `unreachable` routes in
  table `10002`; when the chosen link goes down the kernel deletes its override routes and the
  lookup hits the guard instead of following the VPN or the default route.
* If applying fails half-way, RoutePilot tears down **all** of its state and reports the error,
  so the system returns to its normal routing rather than a partial policy.
* Limitation: rules are compiled when you apply. If the *set* of links changes (e.g. a different
  Wi-Fi), apply again (the GUI re-applies after every rule change).

### 2.3 Routing loops
* A "VPN only" rule never routes the VPN's own server endpoint into the tunnel when the endpoint
  is known; such destinations are skipped with a warning.
* Bypass rules may legitimately include the VPN endpoint — that path is already direct.

### 2.4 Local privilege escalation via the policy file
* The policy file is user-writable by design; root only reads it and validates it with Pydantic.
  A malicious policy can at most express routes/blocks the user could request anyway, and every
  run requires administrator authentication through polkit.
* When installed per-user (the default `scripts/install_desktop.sh`), `pkexec` runs the Python
  interpreter of the user's virtual environment. Anyone who can modify that environment can
  modify what runs as root the next time the user authenticates — exactly as with any
  user-installed admin tool. On shared or hardened machines, install RoutePilot system-wide
  (root-owned) instead.

### 2.5 Crash or desynchronization
* Kernel changes are idempotent: re-applying the same plan is a no-op, and stale routes from
  earlier plans are removed by diffing the owned tables.
* The journal lives on tmpfs, so it disappears together with the (non-persistent) kernel state at
  reboot.
* `routepilot reset` / the "Reset Network State" button / the desktop action
  "Reset RoutePilot network state" always restore a clean state.

### 2.6 Privacy
* No telemetry, analytics or network calls other than DNS lookups for your own domain rules.
* The diagnostics bundle excludes connection names, addresses, rule names and rule targets.

---

## 3. Reporting

Please report vulnerabilities privately, see [SECURITY.md](../../SECURITY.md).
