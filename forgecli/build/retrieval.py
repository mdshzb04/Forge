"""Stage 1 - Forge graph retrieval."""
from __future__ import annotations
import re
from typing import Any
from forgecli.build import BuildContext
from forgecli.graph.repository import GraphNode, GraphSnapshot, RepositoryGraph
_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")
_FILE_LIKE_RE = re.compile(r"^[\w./-]+\.[A-Za-z0-9]+$")
_REPO_HINTS = ("project","repository","repo","code","file","files","architecture","implementation","bug","bugs","docs","documentation","structure","folder","directory","dir","function","method","class","module","current","this","here",)
_STANDALONE_HINTS = ("10 lines","hello world","landing page","button","snippet",)
_RETRIEVAL_CACHE: dict[tuple[int, str, int], str] = {}

def needs_repository_context(prompt: str) -> bool:
    text = (prompt or "").strip().lower()
    if not text:
        return False
    words = set(_TOKEN_RE.findall(text))
    if len(words) <= 4 and any(word in {"hi", "hello", "hey", "howdy", "greetings"} for word in words):
        return False
    if any(hint in text for hint in _STANDALONE_HINTS):
        return False
    if any(ext in text for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".html", ".css", ".yml", ".yaml", ".toml", "package.json")):
        return True
    if any(hint in words for hint in _REPO_HINTS):
        return True
    return "what is this" in text or "explain this" in text or "this project" in text

async def forgegraph_retrieval(context: BuildContext, *, top_k: int = 8) -> BuildContext:
    graph: RepositoryGraph | None = context.extras.get("graph")
    if graph is None or not needs_repository_context(context.prompt):
        context.retrieval = ""
        return context
    try:
        snapshot = await graph.load()
    except Exception as exc:
        context.retrieval = f"[graph: failed to load ({exc!r})]"
        return context
    cache_key = (id(snapshot), context.prompt.strip().lower(), top_k)
    cached = _RETRIEVAL_CACHE.get(cache_key)
    if cached is not None:
        context.retrieval = cached
        return context
    matches = _rank_nodes(snapshot, context.prompt, limit=top_k)
    if not matches:
        context.retrieval = "[graph: no matches]"
        return context
    lines = ["[graph retrieval]"]
    for node, _score in matches:
        location = f" ({node.source_file}:{node.source_location})" if node.source_file else ""
        lines.append(f"- {node.label}{location}")
    context.retrieval = "\n".join(lines)
    _RETRIEVAL_CACHE[cache_key] = context.retrieval
    return context

def _rank_nodes(snapshot: GraphSnapshot, prompt: str, *, limit: int) -> list[tuple[GraphNode, float]]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(prompt)]
    if not tokens:
        return []
    scores: dict[str, float] = {}
    by_id = {n.id: n for n in snapshot.nodes}
    for node in snapshot.nodes:
        score = 0.0
        blob = " ".join(filter(None, [node.label, node.norm_label or "", node.source_file or "", node.source_location or ""])) .lower()
        for token in tokens:
            if token in blob:
                score += 2.0
        if node.source_file and any(token in node.source_file.lower() for token in tokens):
            score += 1.0
        if score:
            scores[node.id] = score
    ranked = sorted(((by_id[nid], score) for nid, score in scores.items()), key=lambda item: (-item[1], item[0].label))
    return ranked[:limit]
