"""Shared test setup: isolate every test run from the developer's real configuration."""

import os
import tempfile

# Must run before any RoutePilot module resolves its config paths.
_SANDBOX = tempfile.mkdtemp(prefix="routepilot-tests-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SANDBOX, "config")
os.environ["XDG_RUNTIME_DIR"] = os.path.join(_SANDBOX, "runtime")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
