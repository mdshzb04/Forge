"""Forge-native loop engineering workflow helpers and CLI command."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forgecli.config.loader import ConfigLoader
from forgecli.config.settings import ForgeSettings
from forgecli.runtime.prepare import build_merged_context, prepare_runtime_sync
from forgecli.utils.paths import ProjectPaths


@dataclass(frozen=True)
class LoopBudget:
    tool: str
    usd_limit: float
    currency: str = "USD"


@dataclass(frozen=True)
class LoopRunRecord:
    iteration: int
    tool: str
    task_status: str
    started_at: str
    finished_at: str
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    estimated_usd: float | None = None
    actual_usd: float | None = None


def loop_root(repo_root: Path) -> Path:
    return repo_root / ".forge" / "loop"


def loop_files(repo_root: Path) -> dict[str, Path]:
    root = loop_root(repo_root)
    return {
        "root": root,
        "workflow": root / "workflow.md",
        "budget": root / "budget.json",
        "run_log": root / "run-log.jsonl",
        "state": root / "state.json",
    }


def ensure_loop_scaffold(repo_root: Path, settings: ForgeSettings | None = None) -> dict[str, Path]:
    settings = settings or _load_settings()
    files = loop_files(repo_root)
    files["root"].mkdir(parents=True, exist_ok=True)

    budget = _build_budget(settings)
    if not files["budget"].exists():
        files["budget"].write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")

    if not files["workflow"].exists():
        files["workflow"].write_text(_workflow_markdown(settings, budget), encoding="utf-8")

    if not files["state"].exists():
        files["state"].write_text(
            json.dumps({"version": 1, "iteration": 0, "last_tool": None}, indent=2) + "\n",
            encoding="utf-8",
        )

    files["run_log"].touch(exist_ok=True)
    return files


def record_loop_run(
    repo_root: Path,
    *,
    tool: str,
    task_status: str,
    iteration: int,
    started_at: datetime,
    finished_at: datetime,
    estimated_input_tokens: int | None = None,
    estimated_output_tokens: int | None = None,
    estimated_usd: float | None = None,
    actual_usd: float | None = None,
) -> Path:
    files = loop_files(repo_root)
    files["root"].mkdir(parents=True, exist_ok=True)
    record = LoopRunRecord(
        iteration=iteration,
        tool=tool,
        task_status=task_status,
        started_at=_iso(started_at),
        finished_at=_iso(finished_at),
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        estimated_usd=estimated_usd,
        actual_usd=actual_usd,
    )
    with files["run_log"].open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    files["state"].write_text(
        json.dumps({"version": 1, "iteration": iteration, "last_tool": tool}, indent=2) + "\n",
        encoding="utf-8",
    )
    return files["run_log"]


def build_loop_context(repo_root: Path, *, force_prepare: bool = False) -> dict[str, Any]:
    prepared = prepare_runtime_sync(repo_root, force=force_prepare, quiet=False)
    merged_context = build_merged_context(prepared.context_summary, prepared.root)
    return {
        "prepared": prepared,
        "merged_context": merged_context,
        "files": ensure_loop_scaffold(prepared.root),
    }


def summarize_loop_files(repo_root: Path) -> dict[str, str]:
    files = loop_files(repo_root)
    return {k: str(v) for k, v in files.items()}


def _load_settings() -> ForgeSettings:
    try:
        return ConfigLoader().load()
    except Exception:
        return ForgeSettings()


def _build_budget(settings: ForgeSettings) -> dict[str, Any]:
    loop = settings.loop_engineering
    return {
        "currency": loop.budget_currency,
        "pattern": loop.pattern,
        "enabled": loop.enabled,
        "low_token_mode": loop.enforce_low_token_mode,
        "configured_limits": {
            "claude": loop.claude_usd_limit,
            "cursor": loop.cursor_usd_limit,
            "codex": loop.codex_usd_limit,
            "antigravity": loop.antigravity_usd_limit,
        },
    }


def _workflow_markdown(settings: ForgeSettings, budget: dict[str, Any]) -> str:
    limits = budget["configured_limits"]
    return (
        "# Forge Loop\n\n"
        f"Pattern: `{budget['pattern']}`\n\n"
        "Workflow:\n"
        "1. Prepare context with Forge.\n"
        "2. Choose the active tool.\n"
        "3. Run a small change.\n"
        "4. Audit the result.\n"
        "5. Tighten prompt/context if needed.\n\n"
        "Configured budgets:\n"
        f"- Claude Code: {budget['currency']} {limits['claude']:.2f}\n"
        f"- Cursor: {budget['currency']} {limits['cursor']:.2f}\n"
        f"- Codex: {budget['currency']} {limits['codex']:.2f}\n"
        f"- Antigravity: {budget['currency']} {limits['antigravity']:.2f}\n\n"
        "These are configured ceilings, not measured spend.\n"
        "Actual spend requires vendor telemetry.\n"
    )


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()
