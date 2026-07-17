"""Forge local graph middleware."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from forgecli.graph.local_engine import LocalCodeGraph
from forgecli.middleware.base import Middleware
from forgecli.runtime_core.request import FileContext

if TYPE_CHECKING:
    from forgecli.middleware.context import RequestContext, ResponseContext

logger = logging.getLogger("forge.middleware.forgegraph")

class ForgeGraphAdapterMiddleware(Middleware):
    def __init__(self, graph: LocalCodeGraph | None = None) -> None:
        self._graph = graph

    @property
    def priority(self) -> int:
        return 400

    async def __call__(self, request: RequestContext, call_next: Callable[[RequestContext], Awaitable[ResponseContext]]) -> ResponseContext:
        graph = self._graph or LocalCodeGraph(Path(request.runtime_context.repository_root))
        try:
            snapshot = await graph.load()
        except Exception as exc:
            logger.debug("Forge graph unavailable: %s", exc)
            return await call_next(request)
        injected = {f.filepath for f in request.ai_request.attached_files}
        matched = 0
        for word in request.ai_request.prompt.split():
            hit = snapshot.search(word, limit=1)
            for node in hit:
                matched += 1
                if node.source_file and node.source_file not in injected:
                    full_path = Path(request.runtime_context.repository_root) / node.source_file
                    if full_path.is_file():
                        request.ai_request.attached_files.append(FileContext(filepath=node.source_file, content=full_path.read_text(encoding='utf-8', errors='replace'), hash_id=f"forgegraph-{node.id}", is_modified=False))
                        injected.add(node.source_file)
        request.metadata["forgegraph_queried"] = True
        request.metadata["forgegraph_matched_nodes_count"] = matched
        return await call_next(request)
