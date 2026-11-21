# ADR 0004: Managed Application Launch via systemd cgroup v2 Scopes

## Status
Proposed — not implemented yet. Application selectors are accepted in the policy file but
skipped (with a warning) when applying. Implementation also needs source NAT, see ADR 0006.

## Context
Routing individual applications is a core user goal. Naive approaches (matching executable name in `/proc` or scraping PIDs) fail because:
1. PIDs are volatile and subject to race conditions.
2. Applications spawn helper processes, child threads, or fork off daemons that do not match the parent binary name.
3. Matching process paths requires invasive netlink socket diag tracking.

## Decision
Implement application routing via **systemd cgroup v2 managed scopes**:
- Applications configured for selective routing are launched via:
  `systemd-run --user --scope --unit=routepilot-app-<id> <binary> [args]`
- In `nftables`, outbound traffic from these sockets is matched deterministically via:
  `socket cgroupv2 level 2 ... meta mark set <mark>`

## Rationale
- Supported in modern Linux kernels (>= 5.4) and systemd.
- Automatically encapsulates all child processes, threads, and subprocesses.
- Clean isolation without requiring `LD_PRELOAD` library injection or kernel ptrace.
