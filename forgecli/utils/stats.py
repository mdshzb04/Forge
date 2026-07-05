"""Helper utilities for tracking and displaying Forge CLI optimization statistics."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from forgecli.runtime.prepare import PreparedRuntime, _scan_repo_light
from forgecli.utils.paths import ProjectPaths


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in the given text (rule of thumb: 4 chars/token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_files_in_layout(context_text: str) -> int:
    """Count the number of files present in the Project layout section of the context."""
    lines = context_text.splitlines()
    file_count = 0
    in_layout = False
    for line in lines:
        if "Project layout (shallow scan):" in line:
            in_layout = True
            continue
        if in_layout:
            if not line.strip():
                # Section ends on first empty line
                continue
            if line.startswith("#") or "Knowledge graph" in line:
                # Reached next section
                break
            clean = line.strip()
            # If it doesn't end with a slash, it's a file, not a directory
            if clean and not clean.endswith("/"):
                file_count += 1
    return file_count


def count_total_files(root: Path) -> int:
    """Recursively count all non-hidden, non-skipped files in the repository."""
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".forge",
        "graphify-out",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
    count = 0
    try:
        for p in root.rglob("*"):
            try:
                rel = p.relative_to(root)
                if any(part.startswith(".") or part in skip_dirs for part in rel.parts[:-1]):
                    continue
                if p.is_file() and not p.name.startswith("."):
                    count += 1
            except (ValueError, OSError):
                continue
    except OSError:
        pass
    return count


def get_graph_build_time(repo_root: Path) -> float | None:
    """Load the recorded Graphify build time if available."""
    build_time_file = repo_root / "graphify-out" / "build_time.json"
    if build_time_file.is_file():
        try:
            with open(build_time_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("build_time")
        except Exception:
            pass
    return None


def record_wrapper_stats(
    wrapper_id: str,
    repo_root: Path,
    prepared: PreparedRuntime,
    prep_time: float,
) -> None:
    """Record context preparation and token optimization statistics to a history file."""
    try:
        raw_context = _scan_repo_light(repo_root)
        optimized_context = prepared.context_summary

        orig_tokens = estimate_tokens(raw_context)
        opt_tokens = estimate_tokens(optimized_context)

        # Enforce non-negative token reduction
        reduction_tokens = max(0, orig_tokens - opt_tokens)
        reduction_pct = (reduction_tokens / orig_tokens * 100) if orig_tokens > 0 else 0.0

        is_reduced = reduction_tokens > 0
        prompt_opt_status = "Enabled" if is_reduced else "Disabled"
        token_opt_status = "Enabled" if is_reduced else "Disabled"

        files_scanned = count_total_files(repo_root)
        relevant_files = count_files_in_layout(optimized_context)
        excluded_files = max(0, files_scanned - relevant_files)

        kg_cache = "Cache Hit" if (repo_root / "graphify-out" / "graph.json").is_file() else "Cache Miss"
        cache_status = "Cache Hit" if prepared.from_cache else "Cache Miss"
        graph_build_time = get_graph_build_time(repo_root)

        stats_data = {
            "cli_used": wrapper_id,
            "repo_name": repo_root.name,
            "kg_cache": kg_cache,
            "prep_time": prep_time,
            "graph_build_time": graph_build_time,
            "original_tokens": orig_tokens,
            "optimized_tokens": opt_tokens,
            "reduction_tokens": reduction_tokens,
            "reduction_pct": reduction_pct,
            "files_scanned": files_scanned,
            "files_count": relevant_files,
            "excluded_files": excluded_files,
            "prompt_opt_status": prompt_opt_status,
            "token_opt_status": token_opt_status,
            "cache_status": cache_status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save to ProjectPaths.data_dir / "stats_history.json"
        paths = ProjectPaths.from_env()
        paths.ensure()
        stats_file = paths.data_dir / "stats_history.json"

        history = []
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass

        if not isinstance(history, list):
            history = []

        history.insert(0, stats_data)
        history = history[:10]  # Maintain only the last 10 runs

        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    except Exception:
        # Prevent any stats failure from interrupting/slowing the CLI execution
        pass


def get_stats_history() -> list[dict[str, Any]]:
    """Retrieve the stored optimization statistics history."""
    try:
        paths = ProjectPaths.from_env()
        stats_file = paths.data_dir / "stats_history.json"
        if not stats_file.exists():
            return []
        with open(stats_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if isinstance(history, list):
                return history
    except Exception:
        pass
    return []
