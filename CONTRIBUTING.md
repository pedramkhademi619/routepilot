# Contributing to RoutePilot

Thanks for helping! Bug reports, translations, docs and code are all welcome.

## Ground rules

* **Hexagonal architecture.** `domain` holds models and ports and imports nothing from Qt,
  subprocesses or the network. `application` holds use cases (`PolicyApplyService`,
  `PlanCompiler`, `ReconciliationService`, …). `infrastructure` implements the ports
  (pyroute2, nftables, systemd-resolved, NetworkManager, JSON files). `cli` and `ui` are thin
  driving adapters.
* **One class per module**, named after the class.
* **The GUI never runs as root.** Anything privileged goes through `routepilot apply|reset`, which
  re-validates its input.
* **Only touch RoutePilot-owned kernel resources** (see `RoutingLayout` and
  [ADR 0006](docs/adr/0006-destination-override-tables.md)). Never `shell=True`.
* **No telemetry.**
* Every user-visible string lives in `src/routepilot/ui/i18n/*.json` — never hard-code text in
  views. All catalogs must have the same keys (a test enforces it).

## Development setup

```bash
git clone https://github.com/pedramkhademi619/routepilot.git
cd routepilot
uv venv && uv pip install -e ".[dev]"   # or: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
source .venv/bin/activate

routepilot-gui --mock      # GUI with a simulated network, safe to click around
routepilot --mock plan     # what 'apply' would do, without touching the kernel
```

## Checks (same as CI)

```bash
ruff check src tests scripts
ruff format --check src tests scripts
mypy src
pytest
```

`tests/integration` runs the real netlink/nftables adapters inside a throwaway network namespace
(`unshare -rn`), so it needs no root and never touches your network. It is skipped automatically
where unprivileged user namespaces are disabled.

To refresh the README screenshots: `python scripts/capture_screenshots.py`.

## Translations

Copy `src/routepilot/ui/i18n/en.json` to `<language-code>.json`, translate the values (keep the
`{placeholders}`), set `language.native_name`, and add the code to `RTL_LANGUAGES` in
`translation_manager.py` if the script is right-to-left. The language then appears in Settings.

## Pull requests

1. Branch from `main` (`fix/…`, `feat/…`).
2. Keep the change focused and add tests for policy/compiler/adapter behaviour.
3. Describe user-visible changes in `CHANGELOG.md` under *Unreleased*.
