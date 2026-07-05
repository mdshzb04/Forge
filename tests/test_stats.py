"""Unit tests for the stats command and metrics utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from forgecli.cli.main import app
from forgecli.runtime.prepare import PreparedRuntime, prepare_runtime_sync
from forgecli.utils.stats import (
    count_files_in_layout,
    estimate_tokens,
    get_stats_history,
    record_wrapper_stats,
)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abc") == 1
    assert estimate_tokens("a" * 40) == 10


def test_count_files_in_layout() -> None:
    context = (
        "Repository: TestRepo\n"
        "Root: /path/to/repo\n"
        "\n"
        "Project layout (shallow scan):\n"
        "file1.py\n"
        "dir/\n"
        "  file2.js\n"
        "  subdir/\n"
        "\n"
        "Knowledge graph already on disk..."
    )
    assert count_files_in_layout(context) == 2


def test_record_and_get_stats_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    prepared = PreparedRuntime(
        root=tmp_path,
        context_summary="Project layout (shallow scan):\nfile1.py\nfile2.py",
        context_file=tmp_path / "context.md",
        from_cache=False,
    )

    assert get_stats_history() == []

    for idx in range(12):
        record_wrapper_stats(
            wrapper_id=f"cli_{idx}",
            repo_root=tmp_path,
            prepared=prepared,
            prep_time=0.05 + idx * 0.01,
        )

    history = get_stats_history()
    assert len(history) == 10
    assert history[0]["cli_used"] == "cli_11"
    assert history[0]["repo_name"] == tmp_path.name
    assert history[0]["files_count"] == 2
    assert history[0]["cache_status"] == "MISS"


def test_stats_cli_no_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "No optimization statistics available yet." in result.output


def test_stats_cli_with_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    # Mock a shrinking repository run
    prepared = PreparedRuntime(
        root=tmp_path,
        context_summary="Project layout (shallow scan):\nfile1.py",
        context_file=tmp_path / "context.md",
        from_cache=True,
    )

    with patch(
        "forgecli.utils.stats._scan_repo_light",
        return_value="Project layout (shallow scan):\nfile1.py\nfile2.py\nfile3.py\nfile4.py\nfile5.py",
    ):
        record_wrapper_stats(
            wrapper_id="claude",
            repo_root=tmp_path,
            prepared=prepared,
            prep_time=0.12345,
        )

    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Forge Optimization Report" in result.output
    assert "AI CLI              : Claude" in result.output
    assert "Estimated Original Tokens  :" in result.output
    assert "Estimated Optimized Tokens :" in result.output
    assert "Estimated Tokens Saved     :" in result.output
    assert "Prompt Optimization : Enabled" in result.output


def test_stats_shrinking_repo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    prepared = PreparedRuntime(
        root=tmp_path,
        context_summary="Project layout (shallow scan):\nfile1.py",
        context_file=tmp_path / "context.md",
        from_cache=False,
    )

    # Scanned mock has 5 lines (more tokens), optimized has 1 file (fewer tokens)
    with patch(
        "forgecli.utils.stats._scan_repo_light",
        return_value="Project layout (shallow scan):\nfile1.py\nfile2.py\nfile3.py\nfile4.py",
    ):
        record_wrapper_stats("cursor", tmp_path, prepared, 0.25)

    history = get_stats_history()
    assert len(history) == 1
    assert history[0]["reduction_tokens"] > 0
    assert history[0]["reduction_pct"] > 0.0
    assert history[0]["prompt_opt_status"] == "Enabled"


def test_stats_same_size_repo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    prepared = PreparedRuntime(
        root=tmp_path,
        context_summary="Project layout (shallow scan):\nfile1.py",
        context_file=tmp_path / "context.md",
        from_cache=False,
    )

    # Scanned is identical to optimized layout
    with patch(
        "forgecli.utils.stats._scan_repo_light",
        return_value="Project layout (shallow scan):\nfile1.py",
    ):
        record_wrapper_stats("cursor", tmp_path, prepared, 0.25)

    history = get_stats_history()
    assert len(history) == 1
    assert history[0]["reduction_tokens"] == 0
    assert history[0]["reduction_pct"] == 0.0
    assert history[0]["prompt_opt_status"] == "Disabled"

    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Repository already fits within the optimization budget." in result.output


def test_stats_growing_repo_falls_back(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    # Mock _scan_repo_light to return a small string
    # Mock _optimize_tokens to return a larger string (simulating growth)
    with (
        patch("forgecli.runtime.prepare._scan_repo_light", return_value="short context"),
        patch(
            "forgecli.runtime.prepare._optimize_tokens", return_value="a very long context indeed"
        ),
        patch("forgecli.runtime.prepare._optimize_prompt", return_value="something"),
    ):
        prepared = prepare_runtime_sync(tmp_path, force=True, quiet=True)

    # Should fall back to the short context
    assert prepared.context_summary == "short context"


def test_record_graph_build_stats(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    from forgecli.utils.stats import record_graph_build_stats

    record_graph_build_stats(
        repo_root=tmp_path,
        build_time=1.4567,
        nodes=20,
        edges=35,
    )

    history = get_stats_history()
    assert len(history) == 1
    assert history[0]["cli_used"] == "graph"
    assert history[0]["status"] == "Graph Built"
    assert history[0]["graph_build_time"] == 1.4567

    runner = CliRunner()
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Status              : ✓ Graph Built" in result.output
    assert "Graph Build Time    : 1.457 s" in result.output
