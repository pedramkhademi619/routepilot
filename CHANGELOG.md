# Changelog

All notable changes to **RoutePilot** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-21

A rework of the routing engine and the desktop UI. Re-apply your policy after upgrading;
leftovers from 0.1.x are cleaned up automatically.

### Changed
- **Routing engine** now pins destinations in RoutePilot-owned tables (`10001` overrides,
  `10002` fail-closed guards) consulted by ip rules at priorities 4810/4820, ahead of common VPN
  clients (sing-box/clash `9000+`, wg-quick). The kernel picks the correct source address and
  enforces fail-closed itself. See ADR 0006.
- Applying is idempotent and diff-based; failures tear down all RoutePilot state.
- Domains are resolved through the DNS servers of the link the traffic will use
  (`resolvectl query -i`), and split-DNS domains are merged with the link's existing domains
  instead of replacing them.
- One CLI: `routepilot status | rules | eval | plan | apply | reset`. `apply` and `reset`
  elevate themselves through polkit (`pkexec`); `routepilot-apply` / `routepilot-recover`
  remain as shortcuts.
- The GUI runs privileged work through `QProcess` (non-blocking, coalesced), refreshes the
  network in the background every 15 s, and shows results in the status bar.
- **Responsive UI**: collapsible icon sidebar, wrapping headers, stacking cards, rules table that
  hides secondary columns on narrow windows, scrollable rule editor, no horizontal scrolling
  down to 480 px.
- New theme system (dark, light, follow system) with themed checkboxes, combo boxes and spin
  boxes; preferences are remembered.
- All UI text moved to JSON catalogs (`ui/i18n`); full Persian translation with correct
  right-to-left layout and bidi handling of domains and IPs.

### Added
- "Through VPN only" rules can target a specific VPN; "while a specific VPN is on" conditions
  have a VPN picker.
- IPv6 routing, IPv6 discovery, real route metrics and connection state from NetworkManager.
- WireGuard and `tun` connections are recognised as VPNs.
- Empty state, confirmation before deleting rules, double-click to edit.
- `routepilot plan` dry run; `--version`; `python -m routepilot`.
- Integration test that drives the real adapters in an unprivileged network namespace.
- Screenshot script for documentation and visual QA.

### Fixed
- Packet marks never matched their mask, so mark-based routing never worked.
- Re-applying duplicated nftables rules.
- Settings and Diagnostics showed raw translation keys.
- Hard-coded `/home/pedram/...` paths broke the app for every other user.
- Root-owned state file in `/tmp` (symlink attack surface) — removed.
- Corrupt policy files were silently replaced by an empty policy on the next save; they are now
  backed up first.
- Tests overwrote the developer's real `~/.config/routepilot/settings.json`.
- Qt timer started from a worker thread; UI blocked during network discovery.
- Several invisible labels, broken spin box arrows and unreadable links in the dark theme.

### Removed
- Site-specific hacks (hard-coded domains and fallback IPs) from the core.
- The non-existent `routepilot-serviced` entry point, its systemd unit and an unused polkit
  policy; the PyInstaller spec.

## [0.1.0] - 2026-11-14

### Added
- First public version: hexagonal architecture, NetworkManager discovery, policy evaluator,
  plan compiler, nftables/pyroute2 adapters, PyQt6 GUI with Overview, Rules, Connections,
  Diagnostics and Settings, CLI and recovery tool.

[Unreleased]: https://github.com/pedramkhademi619/routepilot/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pedramkhademi619/routepilot/releases/tag/v0.2.0
[0.1.0]: https://github.com/pedramkhademi619/routepilot/tree/v0.1.0
