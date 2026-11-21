# ADR 0006: Destination Override Tables Instead of Packet Marks

## Status
Accepted (supersedes the fwmark design sketched in ADR 0001 and used by 0.1.x)

## Context
RoutePilot 0.1 steered traffic by marking packets in an nftables `type route` output chain
(`meta mark set 0x10`) and sending marked packets to table `10001` with
`ip rule fwmark 0x10/0x00ff0000 lookup 10001`. In practice this never worked:

1. **The mark could not match its mask.** `0x10 & 0x00ff0000 == 0`, so the rule never fired.
2. **Source address selection happens before re-routing.** A socket connected while the VPN
   owned the default route already has the VPN's address as its source. Re-routing the packet
   to the physical link afterwards sends it out with the wrong source unless it is also
   masqueraded.
3. **Rule order versus VPN clients.** sing-box/clash TUN clients install their own rules at
   priority `9000+`, wg-quick at `32764`. A rule at `10010` is reached only after those
   clients have already captured the lookup.
4. To compensate, 0.1 also added host routes to the *main* table and tracked them in a
   root-written file under `/tmp`, which polluted system state and was unsafe.

## Decision
Route by **destination**, in RoutePilot-owned tables consulted early in the RPDB:

| Priority | Table   | Contents |
| -------: | :------ | :------- |
| 4810     | `10001` | One route per pinned destination: `via <gw> dev <physical>` for bypass, `dev <tun>` for "VPN only", `throw` for "system default" |
| 4820     | `10002` | `unreachable` routes for fail-closed rules |

* A lookup for a destination that has no route in a table simply falls through to the next
  rule, so unrelated traffic is untouched.
* Because the decision is made during the normal route lookup, the kernel picks the correct
  source address for the chosen egress — no NAT needed.
* Priorities below 9000 run before common VPN clients' rules.
* **Fail-closed is enforced by the kernel**: when the target link goes down, its routes vanish
  from `10001` and the lookup lands on the `unreachable` guard in `10002` instead of leaking.
* Explicit "Block" rules stay in nftables (`table inet routepilot`, `reject` in an output
  filter chain), loaded atomically with a `table … / delete table …` preamble so re-applying
  never duplicates rules.
* Domains are resolved through the DNS servers of the link the traffic will use
  (`resolvectl query -i <link>`), and `~domain` routing domains are added to that link so
  applications resolve the same addresses.

Applying is a diff: desired routes are `replace`d, routes in owned tables that are no longer
desired are deleted, and rules are only re-created when they differ. Teardown removes every
owned rule/table/nft table plus the split DNS domains recorded in the journal.

## Consequences
* Per-application routing cannot be expressed with destination routes; it remains a planned
  feature (ADR 0004) that will need marks **plus** source NAT.
* When CIDRs of different rules overlap, the kernel's longest-prefix match decides; identical
  destinations are resolved by rule priority at compile time.
* Verified end-to-end in an unprivileged network namespace
  (`tests/integration/netns_scenario.py`), including a sing-box style rule at priority 9000.
