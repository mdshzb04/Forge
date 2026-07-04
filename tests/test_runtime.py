"""Tests for the fast runtime preparation layer."""

from __future__ import annotations

import time
from pathlib import Path

from forgecli.runtime.cache_store import (
    CachedRuntime,
    load_runtime_cache,
    repo_fingerprint,
    save_runtime_cache,
)
from forgecli.runtime.prepare import prepare_runtime_sync, resolve_repo_root


def test_resolve_repo_root_falls_back_to_cwd(tmp_path: Path) -> None:
    assert resolve_repo_root(tmp_path) == tmp_path.resolve()


def test_prepare_runtime_is_fast_and_cached(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("FORGECLI_CONFIG_DIR", str(tmp_path / "config"))

    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")

    first = prepare_runtime_sync(tmp_path)
    assert first.from_cache is False
    assert "demo" in first.context_summary or "Repository" in first.context_summary
    assert first.context_file.is_file()

    second = prepare_runtime_sync(tmp_path)
    assert second.from_cache is True


def test_runtime_cache_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGECLI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGECLI_CACHE_DIR", str(tmp_path / "cache"))

    fp = repo_fingerprint(tmp_path)
    ctx_file = tmp_path / "ctx.md"
    ctx_file.write_text("hello", encoding="utf-8")
    save_runtime_cache(
        fp,
        CachedRuntime(
            context_summary="hello",
            context_file=str(ctx_file),
            node_count=0,
            edge_count=0,
            created_at=time.time(),
        ),
    )
    loaded = load_runtime_cache(fp)
    assert loaded is not None
    assert loaded.context_summary == "hello"
