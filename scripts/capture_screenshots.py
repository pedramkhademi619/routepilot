#!/usr/bin/env python3
"""Renders RoutePilot pages with a simulated network into PNG files (README / visual QA).

Usage: QT_QPA_PLATFORM=offscreen python scripts/capture_screenshots.py [output_dir]
Nothing is read from or written to your real configuration.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="routepilot-shots-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from routepilot.application.services.discovery_service import DiscoveryService  # noqa: E402
from routepilot.domain.policy.action_type import ActionType  # noqa: E402
from routepilot.domain.policy.activation_condition import ActivationCondition  # noqa: E402
from routepilot.domain.policy.condition_type import ConditionType  # noqa: E402
from routepilot.domain.policy.policy_action import PolicyAction  # noqa: E402
from routepilot.domain.policy.policy_document import PolicyDocument  # noqa: E402
from routepilot.domain.policy.routing_rule import RoutingRule  # noqa: E402
from routepilot.domain.policy.selector_type import SelectorType  # noqa: E402
from routepilot.domain.policy.traffic_selector import TrafficSelector  # noqa: E402
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (  # noqa: E402
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.mock_discovery_adapter import (  # noqa: E402
    MockDiscoveryAdapter,
)
from routepilot.ui.controllers.privileged_helper import PrivilegedHelper  # noqa: E402
from routepilot.ui.style import ThemeManager  # noqa: E402
from routepilot.ui.translation_manager import TranslationManager  # noqa: E402
from routepilot.ui.views.main_window import MainWindow  # noqa: E402
from routepilot.ui.views.rule_editor_dialog import RuleEditorDialog  # noqa: E402

SAMPLE_RULES = [
    (
        "Local banking",
        SelectorType.DOMAIN_AND_SUBDOMAINS,
        "bank.example",
        ActionType.USE_DIRECT,
        10,
    ),
    ("Streaming at home", SelectorType.DOMAIN, "video.example.net", ActionType.USE_DIRECT, 20),
    ("Office intranet", SelectorType.CIDR, "10.20.0.0/16", ActionType.USE_SELECTED_VPN, 30),
    ("Tracker block", SelectorType.CIDR, "203.0.113.0/24", ActionType.BLOCK, 40),
    ("Printer", SelectorType.IP_ADDRESS, "192.168.1.40", ActionType.FOLLOW_SYSTEM, 90),
]


def build_window(app: QApplication, theme: str, lang: str) -> MainWindow:
    repo = JsonPolicyRepositoryAdapter(Path(tempfile.mkdtemp()) / "policy.json")
    rules = [
        RoutingRule(
            name=name,
            priority=prio,
            selector=TrafficSelector(type=sel, value=value),
            action=PolicyAction(type=action),
            condition=ActivationCondition(
                type=ConditionType.ANY_VPN_ACTIVE
                if action == ActionType.USE_DIRECT
                else ConditionType.ALWAYS
            ),
        )
        for name, sel, value, action, prio in SAMPLE_RULES
    ]
    rules[-1].enabled = False
    repo.save_policy(PolicyDocument(updated_at="", rules=rules))

    discovery = DiscoveryService(MockDiscoveryAdapter())
    asyncio.run(discovery.refresh())
    i18n = TranslationManager.instance()
    i18n.set_language(lang)
    i18n.apply_layout_direction()
    themes = ThemeManager()
    themes.theme = theme
    themes.apply(app)
    window = MainWindow(discovery, repo, PrivilegedHelper(repo.file_path), themes)
    window.diagnostics_view.target_input.setText("www.bank.example")
    window.diagnostics_vm.evaluate_target("www.bank.example")
    return window


def settle(app: QApplication) -> None:
    """Let layouts, deferred deletions and resize events run like in a live event loop."""
    for _ in range(5):
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "screenshots")
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    names = ["overview", "rules", "connections", "diagnostics", "settings"]
    combos = [
        ("dark", "en", (1180, 720)),
        ("light", "en", (1180, 720)),
        ("dark", "en", (520, 820)),
        ("dark", "fa", (1180, 720)),
        ("dark", "fa", (520, 820)),
    ]
    for theme, lang, (width, height) in combos:
        window = build_window(app, theme, lang)
        window.resize(width, height)
        window.show()
        for index, name in enumerate(names):
            window.switch_to_tab(index)
            settle(app)
            window.grab().save(str(out / f"{name}-{theme}-{lang}-{width}.png"))
        dialog = RuleEditorDialog(window.rules_vm.get_rules()[0], parent=window)
        dialog.resize(min(560, width - 40), 640)
        dialog.show()
        settle(app)
        dialog.grab().save(str(out / f"editor-{theme}-{lang}-{width}.png"))
        dialog.close()
        window.close()
    print(f"Saved screenshots to {out}")


if __name__ == "__main__":
    main()
