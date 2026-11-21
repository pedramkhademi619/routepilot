"""Tests for file-based and subprocess-based adapters (no root required)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from factories import rule

from routepilot.application.services.plan_compiler import PlanCompiler
from routepilot.domain.models.route_entry import RouteEntry
from routepilot.domain.policy.policy_document import PolicyDocument
from routepilot.domain.ports.policy_routing_port import PolicyRoutingPort
from routepilot.infrastructure import legacy_state, paths
from routepilot.infrastructure.adapters.json_plan_journal_adapter import JsonPlanJournalAdapter
from routepilot.infrastructure.adapters.json_policy_repository_adapter import (
    JsonPolicyRepositoryAdapter,
)
from routepilot.infrastructure.adapters.systemd_resolved_adapter import SystemdResolvedAdapter


def test_route_entry_normalizes_destination_and_family() -> None:
    assert RouteEntry(destination="203.0.113.7").destination == "203.0.113.7/32"
    assert RouteEntry(destination="10.1.2.3/8").destination == "10.0.0.0/8"
    v6 = RouteEntry(destination="2001:db8::1")
    assert (v6.destination, v6.family) == ("2001:db8::1/128", 6)


def test_policy_repository_round_trip_and_corruption_backup(tmp_path: Path) -> None:
    repo = JsonPolicyRepositoryAdapter(tmp_path / "policy.json")
    repo.save_policy(PolicyDocument(updated_at="", rules=[rule("Bank", "198.51.100.0/24")]))
    assert [r.name for r in repo.load_policy().rules] == ["Bank"]

    (tmp_path / "policy.json").write_text("{ not json", encoding="utf-8")
    assert repo.load_policy().rules == []
    backups = list(tmp_path.glob("policy.json.corrupt-*"))
    assert len(backups) == 1 and backups[0].read_text() == "{ not json"


def test_journal_round_trip(tmp_path: Path) -> None:
    journal = JsonPlanJournalAdapter(tmp_path / "run" / "journal.json")
    assert journal.load() is None
    plan = PlanCompiler().compile([], [])
    journal.save(plan, "committed")
    loaded = journal.load()
    assert loaded is not None and loaded.plan_id == plan.plan_id
    journal.clear()
    assert journal.load() is None


def test_default_paths_follow_xdg() -> None:
    assert paths.policy_file().parent.name == "routepilot"
    assert "routepilot-tests-" in str(paths.policy_file())


def _completed(stdout: str = "", code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def test_resolved_link_query_parses_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SystemdResolvedAdapter()
    adapter.resolvectl_path = "/usr/bin/resolvectl"
    output = (
        "example.ir: 203.0.113.7                       -- link: wlo1\n"
        "            2001:db8::7                       -- link: wlo1\n"
    )
    run = MagicMock(return_value=_completed(output))
    monkeypatch.setattr(subprocess, "run", run)

    assert adapter._query_link("example.ir", "wlo1") == ["203.0.113.7", "2001:db8::7"]
    assert run.call_args.args[0][-3:] == ["-i", "wlo1", "example.ir"]


def test_split_dns_merges_with_existing_link_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SystemdResolvedAdapter()
    adapter.resolvectl_path = "/usr/bin/resolvectl"
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[1:] == ["domain", "wlo1"]:
            return _completed("Link 3 (wlo1): lan ~old.ir\n")
        return _completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    adapter.configure_split_dns("wlo1", ["new.ir"], previous=["old.ir"])
    assert calls[-1][1:] == ["domain", "wlo1", "lan", "~new.ir"]

    adapter.reset_split_dns("wlo1", ["old.ir"])
    assert calls[-1][1:] == ["domain", "wlo1", "lan"]


def test_legacy_cleanup_ignores_files_not_owned_by_root(tmp_path: Path) -> None:
    state = tmp_path / "legacy.json"
    state.write_text(json.dumps(["203.0.113.7"]), encoding="utf-8")
    routing = MagicMock(spec=PolicyRoutingPort)

    # The test runs unprivileged, so the file is user-owned and must be ignored.
    assert legacy_state.remove_legacy_host_routes(routing, state) == 0
    routing.delete_route.assert_not_called()
    assert state.exists()


def test_rules_without_ids_get_stable_ids(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "updated_at": "",
                "rules": [
                    {
                        "name": "Hand written",
                        "selector": {"type": "domain", "value": "example.com"},
                        "action": {"type": "use_direct"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repo = JsonPolicyRepositoryAdapter(path)
    first = repo.load_policy().rules[0].id
    assert repo.load_policy().rules[0].id == first
    assert json.loads(path.read_text(encoding="utf-8"))["rules"][0]["id"] == first
