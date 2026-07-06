"""Stage 1 — ForgeGraph retrieval.

Asks the configured :class:`RepositoryGraph` to find nodes relevant to
the user prompt. The output is a compact text block listing the
matching node labels, files, and edges, which is fed into the LLM as
context in :mod:`forgecli.build.llm`.
"""

from __future__ import annotations

import re
from typing import Any

from forgecli.build import BuildContext
from forgecli.graph.repository import GraphNode, GraphSnapshot, RepositoryGraph

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")
_FILE_LIKE_RE = re.compile(r"^[\w./-]+\.[A-Za-z0-9]+$")
_REPO_HINTS = (
    "project",
    "repository",
    "repo",
    "code",
    "file",
    "files",
    "architecture",
    "implementation",
    "bug",
    "bugs",
    "docs",
    "documentation",
    "structure",
    "folder",
    "directory",
    "dir",
    "function",
    "method",
    "class",
    "module",
    "current",
    "this",
    "here",
)
_STANDALONE_HINTS = (
    "10 lines",
    "hello world",
    "landing page",
    "button",
    "snippet",
)

_RETRIEVAL_CACHE: dict[tuple[int, str, int], str] = {}


def needs_repository_context(prompt: str) -> bool:
    """Return True when the prompt likely needs repository context."""
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


async def forgegraph_retrieval(
    context: BuildContext, *, top_k: int = 8
) -> BuildContext:
    """Return a context with ``context.retrieval`` populated."""
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
        location = (
            f" ({node.source_file}:{node.source_location})"
            if node.source_file
            else ""
        )
        lines.append(f"- {node.label}{location}")
    context.retrieval = "\n".join(lines)
    _RETRIEVAL_CACHE[cache_key] = context.retrieval
    return context


def _rank_nodes(
    snapshot: GraphSnapshot, query: str, *, limit: int
) -> list[tuple[GraphNode, int]]:
    """Return the top ``limit`` nodes most relevant to ``query``.

    Scoring is intentionally simple and deterministic: each token in
    ``query`` contributes one point for every node whose label or
    source file contains the token as a substring. Tokens that look
    like filenames (``foo.py``, ``auth/bar.ts``) get a bonus when
    they match a node's ``source_file`` exactly.
    """
    tokens = [tok.lower() for tok in _TOKEN_RE.findall(query or "")]
    if not tokens:
        return []
    scored: list[tuple[GraphNode, int]] = []
    for node in snapshot.nodes:
        label = (node.label or "").lower()
        source = (node.source_file or "").lower()
        if not label and not source:
            continue
        score = 0
        for token in tokens:
            if token and token in label:
                score += 1
            if token and token in source:
                score += 1
            if (
                _FILE_LIKE_RE.match(token)
                and node.source_file
                and token == node.source_file.lower()
            ):
                score += 3
        if score > 0:
            scored.append((node, score))
    scored.sort(key=lambda pair: (pair[1], pair[0].label), reverse=True)
    return scored[:limit]


__all__ = ["forgegraph_retrieval", "needs_repository_context"]


_ = Any  # keep typing.Any referenced for the test-only type hints
