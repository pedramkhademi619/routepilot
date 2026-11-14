# Changelog

All notable changes to **RoutePilot** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-11-14

### Added
- **Core Architecture:**
  - Strict Hexagonal Architecture (Ports and Adapters) with **1 class per file**.
  - Typed domain models for connections (`NetworkConnection`, `ConnectionKind`, `IPConfig`, `RouteEntry`).
  - Typed policy models (`RoutingRule`, `TrafficSelector`, `ActivationCondition`, `PolicyAction`, `FallbackPolicy`).
- **Application Services:**
  - `DiscoveryService`: Orchestrates live NetworkManager and Netlink discovery.
  - `PolicyEvaluator`: Deterministic rule priority matching, overrides, and plain-language explanation generation.
  - `PlanCompiler`: Compiles policy rules into immutable `RoutePilotPlan` with dedicated routing tables and atomic `table inet routepilot` rulesets.
  - `ReconciliationService`: Manages transactional application, rollback journal (`/run/routepilot/journal.json`), and crash recovery.
- **Infrastructure Adapters:**
  - `NetworkManagerDiscoveryAdapter`: Asynchronous D-Bus discovery using `dbus-fast` and Netlink routing queries.
  - `Pyroute2RoutingAdapter`: Kernel policy routing tables and ip rules management via `pyroute2`.
  - `NftablesFirewallAdapter`: Atomic netfilter ruleset manipulation without touching external firewalls (`ufw`/`firewalld`).
  - `SystemdCgroupAdapter`: Managed application execution via `systemd-run --user --scope`.
  - `SystemdResolvedAdapter`: Split DNS routing domains (`~domain`) and asynchronous DNS resolution.
  - `JsonPolicyRepositoryAdapter`: Versioned schema persistence with atomic file replacement.
  - `MockDiscoveryAdapter`: Offline test fixtures for reproducible testing.
- **PyQt6 Desktop UI:**
  - Complete MVVM architecture (ViewModels and Views).
  - Screens: Overview, Traffic Rules, Rule Editor Dialog, Connections, Diagnostics Simulator, Settings.
  - System Tray integration with visibility toggle.
  - Modern Dark & Light accessible themes.
- **CLI & Recovery:**
  - `routepilot status`, `routepilot rules`, `routepilot eval <target>`, `routepilot reset`.
  - `routepilot-recover`: Standalone emergency purge tool.
