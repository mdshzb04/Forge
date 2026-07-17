"""Tests for the Forge local graph engine."""
from __future__ import annotations

import asyncio
from pathlib import Path

from forgecli.graph.local_engine import LocalCodeGraph


def test_local_graph_builds_snapshot(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("import os\nclass A:\n    def f(self):\n        return 1\n", encoding="utf-8")
    engine = LocalCodeGraph(tmp_path)
    result = asyncio.run(engine.build(force=True))
    snap = result.snapshot
    assert result.artifacts["snapshot"].endswith("snapshot.json")
    assert any(node.label == "mod.py" for node in snap.nodes)
    assert any(edge.relation == "contains" for edge in snap.edges)
