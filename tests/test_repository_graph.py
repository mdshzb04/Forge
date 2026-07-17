"""Tests for the Forge local :class:`RepositoryGraph` adapter."""
from __future__ import annotations

import asyncio
from pathlib import Path

from forgecli.graph.local_engine import LocalCodeGraph


def test_load_and_query_local_graph(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    engine = LocalCodeGraph(tmp_path)
    asyncio.run(engine.build(force=True))
    snap = asyncio.run(engine.load())
    assert snap.search("alpha")
    result = asyncio.run(engine.query("alpha"))
    assert "a.py" in result.answer
