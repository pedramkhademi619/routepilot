# ADR 0005: Staged Apply, Transaction Journal, and Rollback Protocol

## Status
Accepted

## Context
Applying network policy changes can disrupt connectivity if a route gateway is invalid, an interface is missing, or a syntax error occurs. A crash mid-application must never leave the user without direct internet access or in a corrupted firewall state.

## Decision
Apply in a staged, idempotent way:
1. **Validation:** Pydantic models validate the policy; selectors are validated when rules are edited.
2. **Plan Generation:** `PlanCompiler` produces an immutable `RoutePilotPlan` (routes, ip rules,
   nftables table, split DNS) from the rules, the live connections and pre-resolved domains.
3. **Staged Apply:** The plan is written to the journal (`/run/routepilot/journal.json`, tmpfs) with
   status `staged`; then the nftables table is replaced atomically (`nft -f -`), routes in the owned
   tables are converged by diff, and ip rules are reconciled.
4. **Commit or Rollback:** On success the journal is marked `committed` and split DNS is updated
   (best effort). If any kernel step fails, every RoutePilot resource is torn down and a
   `RollbackError` is reported, leaving the system exactly as if RoutePilot was not installed.

`routepilot reset` (alias `routepilot-recover`) purges all RoutePilot tables, rules, the nftables
table and journaled split DNS domains at any time. A post-apply connectivity health check is a
possible future addition.
