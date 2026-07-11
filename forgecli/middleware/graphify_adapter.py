"""Graphify knowledge graph middleware adapter."""



from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from forgecli.middleware.base import Middleware
from forgecli.runtime_core.request import FileContext

if TYPE_CHECKING:

    from forgecli.graph.repository import RepositoryGraph
    from forgecli.middleware.context import RequestContext, ResponseContext



logger = logging.getLogger("forge.middleware.graphify")





class GraphifyAdapterMiddleware(Middleware):

    """Pipeline middleware that uses the RepositoryGraph to enrich code context."""



    def __init__(self, graph: RepositoryGraph) -> None:

        """Initialize the GraphifyAdapterMiddleware.

        Args:
            graph: The RepositoryGraph engine.
        """

        self._graph = graph



    @property

    def priority(self) -> int:

        """Priority ordering value (runs early to fetch context files)."""

        return 400



    async def __call__(

        self,

        request: RequestContext,

        call_next: Callable[[RequestContext], Awaitable[ResponseContext]],

    ) -> ResponseContext:

        """Intercept the request, query repository graph structure, and inject context.

        Args:
            request: The RequestContext object.
            call_next: Next pipeline runner callback.
        """

        if not await self._graph.is_available():

            logger.debug("Graphify backend is not available. Skipping.")

            return await call_next(request)



        try:

            snapshot = await self._graph.load()

        except Exception as e:

            logger.debug("Failed to load repository graph snapshot: %s. Skipping.", e)

            return await call_next(request)







        words = [w.strip() for w in request.ai_request.prompt.split() if len(w) > 3]

        matched_nodes = []

        for word in words:



            clean_word = "".join(c for c in word if c.isalnum() or c in ("_", "."))

            if clean_word:

                hits = snapshot.search(clean_word, limit=3)

                matched_nodes.extend(hits)





        injected_paths = {f.filepath for f in request.ai_request.attached_files}

        for node in matched_nodes:

            source_file = node.source_file

            if source_file and source_file not in injected_paths:



                repo_root = request.runtime_context.repository_root

                full_path = repo_root / source_file

                if full_path.is_file():

                    try:

                        content = full_path.read_text(encoding="utf-8")

                        file_ctx = FileContext(

                            filepath=source_file,

                            content=content,

                            hash_id=f"graphify-node-{node.id}",

                            is_modified=False,

                        )

                        request.ai_request.attached_files.append(file_ctx)

                        injected_paths.add(source_file)

                        logger.info("Graphify injected context file: %s", source_file)

                    except Exception as e:

                        logger.error("Failed to read graphify file %s: %s", source_file, e)





        request.metadata["graphify_queried"] = True

        request.metadata["graphify_matched_nodes_count"] = len(matched_nodes)



        return await call_next(request)

