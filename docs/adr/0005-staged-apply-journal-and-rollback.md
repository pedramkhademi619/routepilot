# ADR 0005: Staged Apply, Transaction Journal, and Rollback Protocol

## Status
Accepted

## Context
Applying network policy changes can disrupt connectivity if a route gateway is invalid, an interface is missing, or a syntax error occurs. A crash mid-application must never leave the user without direct internet access or in a corrupted firewall state.

## Decision
Implement a 5-step staged application and rollback protocol:
1. **Validation:** Pydantic model validation and resource availability check (interfaces, gateways, routing table IDs).
2. **Plan Generation:** Generate an immutable `RoutePilotPlan` representing exact netlink route changes and nftables ruleset fragments.
3. **Staged Apply:** Write plan intent to transaction journal (`/run/routepilot/journal.json`) and apply netfilter ruleset via atomic `nft -f -`.
4. **Verification & Health Check:** Verify packet path / gateway reachability within a timeout window.
5. **Commit or Rollback:** If verification succeeds or user confirms, commit the transaction. If verification fails or service crashes, automatically execute compensating rollback steps.

In addition, provide an independent recovery command `routepilot-recover` that completely purges RoutePilot tables and rules.
