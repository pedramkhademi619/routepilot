# Security Policy

## Supported versions

| Version | Supported |
| :------ | :-------: |
| 0.2.x   | ✅ |
| < 0.2   | ❌ (please upgrade; 0.1.x wrote root-owned state to `/tmp`) |

## Reporting a vulnerability

RoutePilot runs a privileged helper and changes kernel routing, so we take reports about
privilege escalation, traffic leaks, injection or unsafe file handling seriously.

**Please do not open a public issue for security problems.** Instead, use GitHub's
[private vulnerability reporting](https://github.com/pedramkhademi619/routepilot/security/advisories/new).

Helpful details:

1. What is affected and the impact (e.g. local privilege escalation, traffic leaking outside
   the intended path).
2. Steps to reproduce or a proof of concept.
3. Distribution, kernel version, NetworkManager version and the VPN client involved.
4. Output of `routepilot plan` (remove anything private).

You should get an acknowledgement within a few days. Fixes are released as soon as possible and
credited in the changelog unless you prefer otherwise.

The design assumptions are documented in [docs/security/threat_model.md](docs/security/threat_model.md).
