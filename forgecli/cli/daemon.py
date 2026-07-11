"""Forge Context Daemon and MCP Server.

Provides a long-running local background service to monitor repositories,
rebuild context incrementally, and expose HTTP API endpoints and an MCP server.
"""



from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI

from forgecli.runtime.prepare import prepare_runtime_sync, resolve_repo_root
from forgecli.runtime.shared_extraction import (
    extract_dependencies,
    extract_files,
    extract_symbols,
)

_forge_repo_graph_cls = None

_chunker_cls = None

_setup_forgegraph_credentials = None

_httpx = None





def _get_httpx():

    global _httpx

    if _httpx is None:

        import httpx as _h

        _httpx = _h

    return _httpx





def _get_graph():

    global _forge_repo_graph_cls

    if _forge_repo_graph_cls is None:

        from forgecli.graph.backend_forgegraph import ForgeRepositoryGraph
        _forge_repo_graph_cls = ForgeRepositoryGraph

    return _forge_repo_graph_cls





def _get_chunker():

    global _chunker_cls

    if _chunker_cls is None:

        from forgecli.optimizer.chunker import Chunker
        _chunker_cls = Chunker

    return _chunker_cls





def _setup_graph_creds():

    global _setup_forgegraph_credentials

    if _setup_forgegraph_credentials is None:

        from forgecli.cli.commands_graph import setup_forgegraph_credentials as _s

        _setup_forgegraph_credentials = _s

    return _setup_forgegraph_credentials





app = FastAPI(title="Forge Context Runtime API")

watchers: dict[str, RepoWatcher] = {}

watchers_lock = threading.Lock()





def get_recursive_fingerprint(root: Path) -> str:
    """Compute a signature of the repository based on file paths, modification times, and sizes."""
    from forgecli.runtime.shared_extraction import should_skip

    sig = hashlib.sha256()
    sig.update(str(root.resolve()).encode("utf-8"))

    try:
        for path in sorted(root.rglob("*"), key=lambda p: str(p)):
            try:
                parts = path.relative_to(root).parts
                if should_skip(parts):
                    continue
                if path.is_file() and not path.name.startswith("."):
                    stat = path.stat()
                    sig.update(f"{path.name}:{stat.st_mtime}:{stat.st_size}".encode())
            except (ValueError, OSError):
                continue
    except OSError:
        pass



    return sig.hexdigest()[:24]

















class RepoWatcher(threading.Thread):

    """Background thread that monitors a repository and updates cached outputs on change."""



    def __init__(self, root: Path, update_interval: float = 2.0):

        super().__init__(daemon=True)

        self.root = root

        self.update_interval = update_interval

        self.last_fingerprint = ""

        self.running = True



        self.context_summary = ""

        self.context_file = ""

        self.graph_snapshot: Any = None

        self.symbols: list[dict[str, Any]] = []

        self.dependencies: list[dict[str, Any]] = []

        self.files: list[dict[str, Any]] = []

        self.chunks: list[dict[str, Any]] = []

        self.summary_md = ""



        from forgecli.optimizer.orchestrator import OptimizationRuntimeOrchestrator

        self.orchestrator = OptimizationRuntimeOrchestrator(self.root)



    def get_query_optimized_context(self, query: str) -> str:

        return self.orchestrator.get_query_optimized_context(

            query=query,

            files=self.files,

            symbols=self.symbols,

            dependencies=self.dependencies,

        )





    def run(self) -> None:

        while self.running:

            try:

                fingerprint = get_recursive_fingerprint(self.root)

                if fingerprint != self.last_fingerprint:

                    self.last_fingerprint = fingerprint

                    self.refresh_context()

            except Exception:

                pass

            time.sleep(self.update_interval)



    def refresh_context(self) -> None:
        prepared = prepare_runtime_sync(self.root, force=True, quiet=True)
        self.context_summary = prepared.context_summary
        self.context_file = str(prepared.context_file)
        self.files = extract_files(self.root)





        chunker_cls = _get_chunker()
        chunker = chunker_cls(size=4000, overlap=200)

        self.chunks = []

        for file_info in self.files:

            p = self.root / file_info["path"]

            try:

                text = p.read_text(encoding="utf-8", errors="replace")

                file_chunks = chunker.split(text, source_id=file_info["path"])

                for c in file_chunks:

                    self.chunks.append(

                        {

                            "text": c.text,

                            "index": c.index,

                            "start": c.start,

                            "end": c.end,

                            "source_id": c.source_id,

                        }

                    )

            except OSError:

                pass





        graph_cls = _get_graph()
        backend = graph_cls(root=self.root)

        self.graph_snapshot = None



        loop = asyncio.new_event_loop()

        try:

            is_forgegraph = loop.run_until_complete(backend.is_available())

            if is_forgegraph:

                setup_forgegraph_credentials = _setup_graph_creds()

                active_provider = setup_forgegraph_credentials(self.root)

                if active_provider:

                    loop.run_until_complete(backend.update_graph())

                    self.graph_snapshot = loop.run_until_complete(backend.load())

        except Exception:

            pass

        finally:

            loop.close()



        if self.graph_snapshot:

            self.symbols = []

            for node in self.graph_snapshot.nodes:

                self.symbols.append(

                    {

                        "name": node.label,

                        "type": node.file_type or "symbol",

                        "file": node.source_file or "",

                        "line": node.source_location or 1,

                    }

                )



            self.dependencies = []

            for edge in self.graph_snapshot.edges:

                self.dependencies.append(

                    {"source": edge.source, "target": edge.target, "type": edge.relation}

                )

        else:

            self.symbols = extract_symbols(self.root)

            self.dependencies = extract_dependencies(self.root)





        lines = [

            f"# Forge Repository Summary: {self.root.name}",

            f"- **Root Directory:** `{self.root}`",

            f"- **Files Count:** {len(self.files)}",

            f"- **Total Size:** {sum(f['size_bytes'] for f in self.files)} bytes",

            "",

            "## Repository Layout",

        ]

        for f in self.files[:36]:

            lines.append(f"- `{f['path']}` ({f['size_bytes']} bytes)")

        self.summary_md = "\n".join(lines)





def get_watcher_for_path(path: str | Path | None) -> RepoWatcher:

    """Return a cached or newly launched RepoWatcher thread for the specified path."""

    cwd = Path(path or Path.cwd()).resolve()

    root = resolve_repo_root(cwd)

    root_str = str(root)



    with watchers_lock:

        if root_str not in watchers:

            watcher = RepoWatcher(root)

            watcher.start()

            watchers[root_str] = watcher

        return watchers[root_str]





@app.get("/health")

def health(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    return {"status": "ok", "pid": os.getpid(), "root": str(w.root)}





@app.get("/summary")

def get_summary(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    return {

        "markdown": w.summary_md,

        "json": {

            "repository": w.root.name,

            "root": str(w.root),

            "files_count": len(w.files),

            "total_size_bytes": sum(f["size_bytes"] for f in w.files),

            "files": w.files,

        },

    }





@app.get("/context")

def get_context(path: str | None = None, query: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    if query:

        summary = w.get_query_optimized_context(query)

        return {

            "markdown": summary,

            "json": {"summary": summary, "context_file": ""},

        }

    return {

        "markdown": w.context_summary,

        "json": {"summary": w.context_summary, "context_file": w.context_file},

    }





@app.get("/graph")

def get_graph(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    nodes = []

    edges = []

    if w.graph_snapshot:

        nodes = [

            {"id": n.id, "label": n.label, "file_type": n.file_type} for n in w.graph_snapshot.nodes

        ]

        edges = [

            {"source": e.source, "target": e.target, "relation": e.relation}

            for e in w.graph_snapshot.edges

        ]



    md_lines = ["# Knowledge Graph", ""]

    for e in edges[:100]:

        md_lines.append(f"- `{e['source']}` --[{e['relation']}]--> `{e['target']}`")



    return {"markdown": "\n".join(md_lines), "json": {"nodes": nodes, "edges": edges}}





@app.get("/symbols")

def get_symbols(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    md_lines = ["# Codebase Symbols", ""]

    for s in w.symbols[:200]:

        md_lines.append(f"- **{s['name']}** ({s['type']}) in `{s['file']}`:L{s['line']}")



    return {"markdown": "\n".join(md_lines), "json": w.symbols}





@app.get("/dependencies")

def get_dependencies(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    md_lines = ["# Module Dependencies", ""]

    for d in w.dependencies[:200]:

        md_lines.append(f"- `{d['source']}` --[{d['type']}]--> `{d['target']}`")



    return {"markdown": "\n".join(md_lines), "json": w.dependencies}





@app.get("/files")

def get_files(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    md_lines = ["# Repository Files", ""]

    for f in w.files:

        md_lines.append(f"- `{f['path']}` ({f['size_bytes']} bytes)")



    return {"markdown": "\n".join(md_lines), "json": w.files}





@app.get("/chunks")

def get_chunks(path: str | None = None) -> dict[str, Any]:

    w = get_watcher_for_path(path)

    md_lines = ["# Code Chunks", ""]

    for idx, c in enumerate(w.chunks[:100]):

        md_lines.append(f"### Chunk {idx} (from `{c['source_id']}`)")

        md_lines.append("```")

        md_lines.append(c["text"][:300] + "...")

        md_lines.append("```")

        md_lines.append("")



    return {"markdown": "\n".join(md_lines), "json": w.chunks}





def run_mcp_stdio() -> None:
    """Run the stdio MCP protocol handler, passing requests to the local daemon."""
    from forgecli.cli.daemon_utils import check_daemon_health, start_daemon_background

    daemon_url = "http://127.0.0.1:16868"

    if not check_daemon_health():
        start_daemon_background()
        for _ in range(20):
            if check_daemon_health():
                break
            time.sleep(0.2)



    sys.stderr.write("Forge MCP Server active over stdio.\n")

    sys.stderr.flush()



    httpx = _get_httpx()

    with httpx.Client(timeout=15.0) as client:

        for line in sys.stdin:

            if not line.strip():

                continue

            try:

                req = json.loads(line)

                req_id = req.get("id")

                method = req.get("method")

                params = req.get("params", {})



                if method == "initialize":

                    res = {

                        "jsonrpc": "2.0",

                        "id": req_id,

                        "result": {

                            "protocolVersion": "2024-11-05",

                            "capabilities": {"tools": {}},

                            "serverInfo": {"name": "forge", "version": "0.1.0"},

                        },

                    }

                    sys.stdout.write(json.dumps(res) + "\n")

                    sys.stdout.flush()

                elif method == "notifications/initialized":

                    continue

                elif method == "tools/list":

                    res = {

                        "jsonrpc": "2.0",

                        "id": req_id,

                        "result": {

                            "tools": [

                                {

                                    "name": "get_summary",

                                    "description": "Get a summary of the repository layout, file count, and size.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            }

                                        },

                                    },

                                },

                                {

                                    "name": "get_optimized_context",

                                    "description": "Get the fully optimized and compressed codebase context.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            },

                                            "query": {

                                                "type": "string",

                                                "description": "Optional user query to filter relevant files and symbols.",

                                            }

                                        },

                                    },

                                },

                                {

                                    "name": "get_dependency_graph",

                                    "description": "Get file/module dependency relationships.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            }

                                        },

                                    },

                                },

                                {

                                    "name": "file_lookup",

                                    "description": "Retrieve file contents or metadata by relative path.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "file_path": {

                                                "type": "string",

                                                "description": "Relative file path.",

                                            },

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            },

                                        },

                                        "required": ["file_path"],

                                    },

                                },

                                {

                                    "name": "symbol_lookup",

                                    "description": "Lookup symbol definitions (classes/functions) and locations.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "query": {

                                                "type": "string",

                                                "description": "Symbol name search query.",

                                            },

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            },

                                        },

                                    },

                                },

                                {

                                    "name": "semantic_search",

                                    "description": "Search codebase context using keyword/phrase matching.",

                                    "inputSchema": {

                                        "type": "object",

                                        "properties": {

                                            "query": {

                                                "type": "string",

                                                "description": "Search term.",

                                            },

                                            "path": {

                                                "type": "string",

                                                "description": "Optional repository path.",

                                            },

                                        },

                                        "required": ["query"],

                                    },

                                },

                            ]

                        },

                    }

                    sys.stdout.write(json.dumps(res) + "\n")

                    sys.stdout.flush()

                elif method == "tools/call":

                    tool_name = params.get("name")

                    args = params.get("arguments", {})

                    path_param = args.get("path", str(Path.cwd()))



                    try:

                        content = ""

                        if tool_name == "get_summary":

                            r = client.get(f"{daemon_url}/summary?path={path_param}")

                            content = r.json()["markdown"]

                        elif tool_name == "get_optimized_context":

                            env_context = os.environ.get("FORGE_CONTEXT")

                            if env_context:

                                content = env_context

                            else:

                                query_val = args.get("query", "")

                                r = client.get(f"{daemon_url}/context?path={path_param}&query={query_val}")

                                content = r.json()["markdown"]

                                try:

                                    from forgecli.runtime.prepare import build_behavior_instructions

                                    behavior = build_behavior_instructions()

                                    if behavior:

                                        content = behavior + "\n" + content

                                except Exception:

                                    pass

                        elif tool_name == "get_dependency_graph":

                            r = client.get(f"{daemon_url}/dependencies?path={path_param}")

                            content = r.json()["markdown"]

                        elif tool_name == "file_lookup":

                            file_path = args.get("file_path")

                            r = client.get(f"{daemon_url}/files?path={path_param}")

                            files_list = r.json()["json"]

                            matched = next((f for f in files_list if f["path"] == file_path), None)

                            if matched:

                                p = Path(path_param) / file_path

                                try:

                                    content = p.read_text(encoding="utf-8", errors="replace")

                                except Exception as e:

                                    content = f"Error reading file: {e}"

                            else:

                                content = f"File {file_path} not found in repository."

                        elif tool_name == "symbol_lookup":

                            query = args.get("query", "")

                            r = client.get(f"{daemon_url}/symbols?path={path_param}")

                            symbols = r.json()["json"]

                            matches = [s for s in symbols if query.lower() in s["name"].lower()]

                            if matches:

                                content = "\n".join(

                                    f"- **{m['name']}** ({m['type']}) in `{m['file']}`:L{m['line']}"

                                    for m in matches

                                )

                            else:

                                content = f"No symbols matching '{query}' found."

                        elif tool_name == "semantic_search":

                            query = args.get("query", "")

                            r = client.get(f"{daemon_url}/chunks?path={path_param}")

                            chunks = r.json()["json"]

                            matches = [c for c in chunks if query.lower() in c["text"].lower()]

                            if matches:

                                lines = []

                                for idx, m in enumerate(matches[:5]):

                                    lines.append(f"### Match {idx + 1} in `{m['source_id']}`")

                                    lines.append("```")

                                    lines.append(

                                        m["text"][:500] + ("..." if len(m["text"]) > 500 else "")

                                    )

                                    lines.append("```")

                                    lines.append("")

                                content = "\n".join(lines)

                            else:

                                content = f"No matches found for search query '{query}'."

                        else:

                            content = f"Unknown tool: {tool_name}"

                    except Exception as e:

                        content = f"Error communicating with Forge daemon: {e}"



                    res = {

                        "jsonrpc": "2.0",

                        "id": req_id,

                        "result": {"content": [{"type": "text", "text": content}]},

                    }

                    sys.stdout.write(json.dumps(res) + "\n")

                    sys.stdout.flush()

                else:

                    if req_id is not None:

                        res = {

                            "jsonrpc": "2.0",

                            "id": req_id,

                            "error": {"code": -32601, "message": f"Method not found: {method}"},

                        }

                        sys.stdout.write(json.dumps(res) + "\n")

                        sys.stdout.flush()

            except Exception as e:

                sys.stderr.write(f"Error handling line: {e}\n")

                sys.stderr.flush()





if __name__ == "__main__":





    get_watcher_for_path(Path.cwd())

    uvicorn.run(app, host="127.0.0.1", port=16868, log_level="warning")

