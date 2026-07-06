"""Repository graph: indexing, parsing, code intelligence.

The package exposes two layers:

* A small in-memory graph (:class:`CodeGraph`, :class:`Node`, :class:`Edge`)
  used by lightweight callers and tests.
* A back-end abstraction (:class:`RepositoryGraph`) implemented by
  :class:`ForgeRepositoryGraph`, which delegates to the external
  ForgeGraph CLI.
"""

from forgecli.graph.backend_forgegraph import ForgeRepositoryGraph
from forgecli.graph.edge import Edge, EdgeKind
from forgecli.graph.forgegraph import (
    ForgeGraphArtifacts,
    ForgeGraphBuildOutcome,
    ForgeGraphClient,
    ForgeGraphInvocationError,
    ForgeGraphNotFoundError,
)
from forgecli.graph.graph import CodeGraph
from forgecli.graph.indexer import Indexer
from forgecli.graph.node import Node, NodeKind
from forgecli.graph.repository import (
    BuildResult,
    ExplainResult,
    GraphCommunity,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    QueryResult,
    RepositoryGraph,
)

__all__ = [
    "BuildResult",
    "CodeGraph",
    "Edge",
    "EdgeKind",
    "ExplainResult",
    "ForgeGraphArtifacts",
    "ForgeGraphBuildOutcome",
    "ForgeGraphClient",
    "ForgeGraphInvocationError",
    "ForgeGraphNotFoundError",
    "ForgeRepositoryGraph",
    "GraphCommunity",
    "GraphEdge",
    "GraphNode",
    "GraphSnapshot",
    "Indexer",
    "Node",
    "NodeKind",
    "QueryResult",
    "RepositoryGraph",
]
