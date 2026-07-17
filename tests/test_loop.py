"""Tests for the Forge loop engineering workflow."""

from __future__ import annotations

import json
from pathlib import Path

import tomllib
from typer.testing import CliRunner

from forgecli.cli.main import app
from forgecli.loop import ensure_loop_scaffold, loop_files, record_loop_run


def test_config_persists_loop_budget(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "config",
            "--loop-pattern",
            "plan -> run -> audit -> tighten",
            "--claude-usd-limit",
            "2.5",
            "--cursor-usd-limit",
            "2.0",
            "--codex-usd-limit",
            "1.5",
            "--antigravity-usd-limit",
            "3.0",
        ],
    )

    assert result.exit_code == 0
    data = tomllib.loads((tmp_path / "forgecli.toml").read_text(encoding="utf-8"))
    loop = data["loop_engineering"]
    assert loop["pattern"] == "plan -> run -> audit -> tighten"
    assert loop["claude_usd_limit"] == 2.5
    assert loop["cursor_usd_limit"] == 2.0
    assert loop["codex_usd_limit"] == 1.5
    assert loop["antigravity_usd_limit"] == 3.0


def test_loop_command_scaffolds_files_and_logs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "-p", str(tmp_path), "--tool", "codex", "--task", "refine"])

    assert result.exit_code == 0
    files = loop_files(tmp_path)
    assert files["budget"].exists()
    assert files["workflow"].exists()
    assert files["run_log"].exists()
    assert files["state"].exists()

    budget = json.loads(files["budget"].read_text(encoding="utf-8"))
    assert "configured_limits" in budget
    assert budget["configured_limits"]["codex"] >= 0

    run_log = files["run_log"].read_text(encoding="utf-8").strip().splitlines()
    assert len(run_log) == 1
    entry = json.loads(run_log[0])
    assert entry["tool"] == "codex"
    assert entry["task_status"] == "task:refine"


def test_loop_scaffold_idempotent(tmp_path: Path) -> None:
    files = ensure_loop_scaffold(tmp_path)
    before = files["budget"].read_text(encoding="utf-8")
    ensure_loop_scaffold(tmp_path)
    after = files["budget"].read_text(encoding="utf-8")
    assert before == after

