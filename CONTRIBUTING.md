# Contributing to RoutePilot

Thank you for your interest in contributing to **RoutePilot**! We are committed to building an open-source, production-grade Linux desktop networking tool that respects user freedom, security, and honest technical boundaries.

---

## 1. Architectural Principles

1. **Strict Hexagonal Architecture (Ports and Adapters):**
   - The **Domain** contains business entities, value objects, and ports (interfaces). It must never import from Qt, shell execution, or concrete infrastructure libraries.
   - The **Application** layer coordinates use cases and compiles execution plans.
   - **Infrastructure Adapters** implement ports (NetworkManager D-Bus, pyroute2 Netlink, nftables, systemd-resolved, persistence).
   - **Driving Adapters** (PyQt6 UI, CLI) consume application services.
2. **Strict Rule: Only 1 Class in 1 File:**
   - Every entity, value object, port, adapter, viewmodel, view, and exception must reside in its own dedicated Python module.
3. **Privilege Separation:**
   - The PyQt6 desktop GUI must *never* run as root.
   - All kernel mutations are confined to `table inet routepilot` and designated routing tables (`10001`–`10099`).
   - `shell=True` is strictly prohibited.
4. **No Telemetry:**
   - RoutePilot contains zero telemetry, analytics, cloud tracking, or external pings.

---

## 2. Development Setup

We use `uv` for reproducible Python package management:

```bash
# Clone the repository
git clone https://github.com/routepilot/routepilot.git
cd routepilot

# Create virtual environment and install development dependencies
uv venv --python /usr/bin/python3 .venv
uv pip install -e ".[dev]"

# Activate environment
source .venv/bin/activate
```

---

## 3. Running Checks and Tests

Prior to submitting a pull request, all automated checks must pass:

```bash
# 1. Linting and formatting
ruff check src/ tests/
ruff format --check src/ tests/

# 2. Static type checking (mypy)
mypy src/routepilot/domain src/routepilot/application src/routepilot/infrastructure

# 3. Unit and UI test suite (offscreen Qt)
QT_QPA_PLATFORM=offscreen pytest tests/
```

---

## 4. Submitting a Pull Request

1. Fork the repository and create a descriptive branch: `feature/xyz` or `fix/xyz`.
2. Follow our coding guidelines and write unit tests for any new policy logic or adapter behavior.
3. Keep pull requests focused on a single change.
