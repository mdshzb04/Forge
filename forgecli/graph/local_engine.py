"""Forge-native local code graph engine."""
from __future__ import annotations

import ast
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from forgecli.graph.repository import BuildResult, ExplainResult, GraphCommunity, GraphEdge, GraphNode, GraphSnapshot, QueryResult, RepositoryGraph

SNAPSHOT_DIR = ".forge-graph"
SNAPSHOT_FILE = "snapshot.json"
SOURCE_EXTENSIONS = {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs"}

@dataclass(frozen=True)
class _FileIndex:
    path: Path
    rel: str
    language: str | None
    imports: tuple[str, ...]
    symbols: tuple[GraphNode, ...]

class LocalCodeGraph(RepositoryGraph):
    name = "forge-local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.snapshot_path = self.root / SNAPSHOT_DIR / SNAPSHOT_FILE
        self._snapshot: GraphSnapshot | None = None

    async def is_available(self) -> bool:
        return True

    async def build(self, *, force: bool = False) -> BuildResult:
        if self.snapshot_path.exists() and not force:
            snapshot = await self.load()
            return BuildResult(snapshot=snapshot, artifacts={"snapshot": str(self.snapshot_path)})
        snapshot = self._build_snapshot()
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(_snapshot_to_dict(snapshot), indent=2), encoding="utf-8")
        self._snapshot = snapshot
        return BuildResult(snapshot=snapshot, artifacts={"snapshot": str(self.snapshot_path)})

    async def load(self) -> GraphSnapshot:
        if self._snapshot is not None:
            return self._snapshot
        if self.snapshot_path.exists():
            self._snapshot = _snapshot_from_dict(json.loads(self.snapshot_path.read_text(encoding="utf-8")))
            return self._snapshot
        self._snapshot = self._build_snapshot()
        return self._snapshot

    async def query(self, question: str, *, budget: int = 2000) -> QueryResult:
        snapshot = await self.load()
        ranked = _rank_nodes(snapshot, question, limit=max(1, min(8, budget // 250 or 1)))
        cited = tuple(node.source_file or node.label for node, _ in ranked)
        if cited:
            answer = "Relevant files: " + ", ".join(cited)
        else:
            answer = "No direct matches found."
        return QueryResult(question=question, answer=answer, cited_nodes=cited, extra={"matched_nodes": len(ranked)})

    async def explain(self, target: str) -> ExplainResult:
        snapshot = await self.load()
        node = _resolve_node(snapshot, target)
        if node is None:
            return ExplainResult(target=target, explanation=f"No node found for {target}.")
        related = tuple(_related_nodes(snapshot, node))
        refs = sum(1 for edge in snapshot.edges if edge.source == node.id or edge.target == node.id)
        explanation = f"{node.label} in {node.source_file or 'repository'} has {refs} direct relationships."
        return ExplainResult(target=target, explanation=explanation, related=related, extra={"relationships": refs})

    async def shortest_path(self, a: str, b: str) -> list[GraphEdge]:
        snapshot = await self.load()
        start = _resolve_node(snapshot, a)
        goal = _resolve_node(snapshot, b)
        if start is None or goal is None:
            return []
        return _bfs_path(snapshot, start.id, goal.id)

    async def affected(self, target: str, *, relation: Any | None = None, depth: int = 2) -> list[GraphEdge]:
        snapshot = await self.load()
        node = _resolve_node(snapshot, target)
        if node is None:
            return []
        allowed = set(relation) if relation else None
        frontier = {node.id}
        seen = {node.id}
        result: list[GraphEdge] = []
        for _ in range(max(depth, 1)):
            next_frontier: set[str] = set()
            for edge in snapshot.edges:
                if edge.target in frontier and edge.source not in seen and (allowed is None or edge.relation in allowed):
                    result.append(edge)
                    next_frontier.add(edge.source)
                    seen.add(edge.source)
            frontier = next_frontier
            if not frontier:
                break
        return result

    def _build_snapshot(self) -> GraphSnapshot:
        files = [_index_file(path, self.root) for path in _iter_source_files(self.root)]
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        file_node_ids: dict[str, str] = {}
        symbol_names: dict[str, list[str]] = defaultdict(list)
        symbol_by_fqn: dict[str, GraphNode] = {}

        for item in files:
            file_id = f"file:{item.rel}"
            file_node_ids[item.rel] = file_id
            nodes.append(GraphNode(id=file_id, label=item.path.name, file_type=item.language, source_file=item.rel, norm_label=item.rel.lower(), extra={"kind": "file"}))
            for sym in item.symbols:
                symbol_by_fqn[sym.id] = sym
                symbol_names[sym.label].append(sym.id)
                nodes.append(sym)
                edges.append(GraphEdge(source=file_id, target=sym.id, relation="contains", source_file=item.rel, source_location=sym.source_location, extra={"kind": "containment"}))

        for item in files:
            file_id = file_node_ids[item.rel]
            for imported in item.imports:
                target = _resolve_import_target(imported, item.rel, file_node_ids, symbol_names)
                if target is not None:
                    edges.append(GraphEdge(source=file_id, target=target, relation="imports", source_file=item.rel, extra={"import": imported}))

        for item in files:
            for sym in item.symbols:
                if sym.extra.get("calls"):
                    for callee in sym.extra["calls"]:
                        target = _resolve_symbol_name(callee, symbol_names)
                        if target is not None:
                            edges.append(GraphEdge(source=sym.id, target=target, relation="calls", source_file=item.rel, extra={"callee": callee}))
                if sym.extra.get("references"):
                    for ref in sym.extra["references"]:
                        target = _resolve_symbol_name(ref, symbol_names)
                        if target is not None:
                            edges.append(GraphEdge(source=sym.id, target=target, relation="references", source_file=item.rel, extra={"reference": ref}))

        metadata = {
            "files": len(files),
            "languages": sorted({item.language for item in files if item.language}),
            "symbols": sum(len(item.symbols) for item in files),
            "local_engine": True,
        }
        communities = (GraphCommunity(id=0, size=len(nodes), label="repository", members=tuple(n.id for n in nodes)),) if nodes else ()
        return GraphSnapshot(root=str(self.root), nodes=tuple(nodes), edges=tuple(_dedupe_edges(edges)), communities=communities, metadata=metadata)


def _iter_source_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS and ".forge-graph" not in path.parts:
            yield path


def _index_file(path: Path, root: Path) -> _FileIndex:
    rel = str(path.relative_to(root))
    text = path.read_text(encoding="utf-8", errors="replace")
    imports: list[str] = []
    symbols: list[GraphNode] = []
    language = _language_for(path)
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            imports.extend(_python_imports(tree))
            symbols.extend(_python_symbols(tree, rel, text))
    return _FileIndex(path=path, rel=rel, language=language, imports=tuple(dict.fromkeys(imports)), symbols=tuple(symbols))


def _python_imports(tree: ast.AST) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                out.append(f"{mod}.{alias.name}" if mod else alias.name)
    return out


def _python_symbols(tree: ast.AST, rel: str, text: str) -> list[GraphNode]:
    out: list[GraphNode] = []
    lines = text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else ("method" if any(isinstance(parent, ast.ClassDef) for parent in ast.walk(node) if parent is not node) else "function")
            source_location = f"{node.lineno}:{getattr(node, 'end_lineno', node.lineno)}"
            body_text = _extract_text(lines, node.lineno, getattr(node, "end_lineno", node.lineno))
            calls = tuple(sorted({callee for callee in _collect_calls(node)}))
            refs = tuple(sorted({ref for ref in _collect_names(node)} - {node.name}))
            out.append(GraphNode(id=f"{rel}:{node.lineno}:{node.name}", label=node.name, file_type=kind, source_file=rel, source_location=source_location, norm_label=node.name.lower(), extra={"calls": calls, "references": refs, "signature": body_text.splitlines()[0].strip() if body_text else node.name}))
    return out


def _collect_calls(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


def _collect_names(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _extract_text(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[max(0, start - 1):max(0, end)])


def _language_for(path: Path) -> str | None:
    return {".py": "python", ".pyi": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript", ".go": "go", ".rs": "rust"}.get(path.suffix.lower())


def _resolve_import_target(imported: str, rel: str, file_node_ids: dict[str, str], symbol_names: dict[str, list[str]]) -> str | None:
    candidates = [imported, imported.split(".")[-1]]
    for candidate in candidates:
        if candidate in file_node_ids:
            return file_node_ids[candidate]
        if candidate in symbol_names:
            return symbol_names[candidate][0]
    return None


def _resolve_symbol_name(name: str, symbol_names: dict[str, list[str]]) -> str | None:
    if name in symbol_names:
        return symbol_names[name][0]
    return None


def _resolve_node(snapshot: GraphSnapshot, target: str) -> GraphNode | None:
    for node in snapshot.nodes:
        if target in {node.id, node.label, node.source_file, node.norm_label}:
            return node
    for node in snapshot.nodes:
        if target.lower() in (node.label or "").lower() or target.lower() in (node.norm_label or "").lower():
            return node
    return None


def _related_nodes(snapshot: GraphSnapshot, node: GraphNode) -> list[GraphNode]:
    related: list[GraphNode] = []
    for edge in snapshot.neighbors(node.id):
        other = snapshot.node(edge.target if edge.source == node.id else edge.source)
        if other is not None and other.id != node.id:
            related.append(other)
    return related[:10]


def _rank_nodes(snapshot: GraphSnapshot, prompt: str, *, limit: int) -> list[tuple[GraphNode, float]]:
    tokens = {token.lower() for token in prompt.replace("/", " ").replace("-", " ").split() if token}
    scored: list[tuple[GraphNode, float]] = []
    for node in snapshot.nodes:
        hay = " ".join(filter(None, [node.label, node.source_file, node.source_location, node.norm_label, str(node.extra.get("signature", ""))])).lower()
        score = sum(2.5 for token in tokens if token and token in hay)
        score += sum(0.5 for token in tokens if token and token == (node.label or "").lower())
        if score:
            scored.append((node, score))
    return sorted(scored, key=lambda item: (-item[1], item[0].label))[:limit]


def _bfs_path(snapshot: GraphSnapshot, start: str, goal: str) -> list[GraphEdge]:
    adjacency: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in snapshot.edges:
        adjacency[edge.source].append(edge)
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        for edge in adjacency.get(current, []):
            if edge.target not in seen:
                seen.add(edge.target)
                queue.append((edge.target, path + [edge]))
    return []


def _dedupe_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    seen: set[tuple[str, str, str]] = set()
    out: list[GraphEdge] = []
    for edge in edges:
        key = (edge.source, edge.target, edge.relation)
        if key not in seen:
            seen.add(key)
            out.append(edge)
    return out


def _snapshot_to_dict(snapshot: GraphSnapshot) -> dict[str, Any]:
    return {"root": snapshot.root, "nodes": [asdict(n) for n in snapshot.nodes], "edges": [asdict(e) for e in snapshot.edges], "communities": [asdict(c) for c in snapshot.communities], "metadata": snapshot.metadata, "directed": snapshot.directed, "multigraph": snapshot.multigraph}


def _snapshot_from_dict(data: dict[str, Any]) -> GraphSnapshot:
    return GraphSnapshot(root=data["root"], nodes=tuple(GraphNode(**n) for n in data.get("nodes", [])), edges=tuple(GraphEdge(**e) for e in data.get("edges", [])), communities=tuple(GraphCommunity(**c) for c in data.get("communities", [])), directed=data.get("directed", False), multigraph=data.get("multigraph", False), metadata=data.get("metadata", {}))
