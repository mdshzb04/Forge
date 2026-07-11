"""Native Python repository graph builder.

Builds a graph.json compatible with the ForgeGraph backend, removing the
external binary dependency. Uses the shared extraction module and tree-sitter
for structural analysis. Falls back gracefully when tree-sitter is unavailable.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from forgecli.runtime.shared_extraction import (
    extract_dependencies,
    extract_files,
    extract_symbols,
)

DEFAULT_OUTPUT_DIR = "forgegraph-out"


def build_native_graph(root: Path) -> dict[str, Any]:
    """Build a native graph.json from repository extraction.

    Returns the payload in the same shape as the ForgeGraph CLI produces.
    """
    root = root.resolve()
    symbols = extract_symbols(root)
    deps = extract_dependencies(root)
    files = extract_files(root)

    symbol_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in symbols:
        symbol_index[s["file"]].append(s)

    node_map: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    node_id_counter = 0

    for file_info in files:
        rel = file_info["path"]
        nid = f"n{node_id_counter}"
        node_id_counter += 1
        node_map[rel] = nid
        suffix = Path(rel).suffix.lstrip(".")
        nodes.append({
            "id": nid,
            "label": rel,
            "file_type": suffix if suffix else "unknown",
            "source_file": rel,
            "source_location": None,
            "community": None,
            "norm_label": rel.lower(),
        })

    for s_obj in symbols:
        nid = f"n{node_id_counter}"
        node_id_counter += 1
        name = s_obj["name"]
        kind = s_obj["type"]
        file_rel = s_obj["file"]
        line = s_obj.get("line", 1)
        nodes.append({
            "id": nid,
            "label": name,
            "file_type": None,
            "source_file": file_rel,
            "source_location": f"{file_rel}:{line}",
            "community": None,
            "norm_label": name.lower(),
            "symbol_type": kind,
        })
        parent_nid = node_map.get(file_rel)
        if parent_nid:
            links.append({
                "source": parent_nid,
                "target": nid,
                "relation": "contains",
                "confidence": "high",
                "confidence_score": 0.95,
                "source_file": file_rel,
                "source_location": None,
                "weight": 1.0,
            })

    for dep in deps:
        source_rel = dep["source"]
        target = dep["target"]
        dep_type = dep["type"]
        source_nid = node_map.get(source_rel)
        target_nid = node_map.get(target)
        if source_nid is None or target_nid is None:
            continue
        links.append({
            "source": source_nid,
            "target": target_nid,
            "relation": dep_type,
            "confidence": "high",
            "confidence_score": 0.9,
            "source_file": source_rel,
            "source_location": None,
            "weight": 1.0,
        })

    return {
        "directed": True,
        "multigraph": False,
        "nodes": nodes,
        "links": links,
        "hyperedges": [],
        "community_labels": {},
        "metadata": {
            "builder": "native",
            "build_time": time.time(),
            "root": str(root),
            "files_count": len(files),
            "symbols_count": len(symbols),
            "deps_count": len(deps),
        },
    }


class NativeGraphBuilder:
    """Native graph builder that writes graph.json without external binaries."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def build(self, *, force: bool = False) -> dict[str, Any]:
        out_dir = self.root / DEFAULT_OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        graph_path = out_dir / "graph.json"

        if graph_path.exists() and not force:
            return json.loads(graph_path.read_text(encoding="utf-8"))

        payload = build_native_graph(self.root)
        graph_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        manifest = {
            "root": str(self.root),
            "build_time": time.time(),
            "builder": "native",
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return payload

    @staticmethod
    def is_available() -> bool:
        return True
