"""Forge Context Daemon and MCP Server.

Provides a long-running local background service to monitor repositories,
rebuild context incrementally, and expose HTTP API endpoints and an MCP server.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI

from forgecli.cli.commands_graph import setup_graphify_credentials
from forgecli.graph.backend_graphify import GraphifyRepositoryGraph
from forgecli.optimizer.chunker import Chunker
from forgecli.runtime.prepare import prepare_runtime_sync, resolve_repo_root

app = FastAPI(title="Forge Context Runtime API")
watchers: dict[str, RepoWatcher] = {}
watchers_lock = threading.Lock()


def get_recursive_fingerprint(root: Path) -> str:
    """Compute a signature of the repository based on file paths, modification times, and sizes."""
    sig = hashlib.sha256()
    sig.update(str(root.resolve()).encode("utf-8"))

    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".forge",
        "graphify-out",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }

    try:
        for path in sorted(root.rglob("*"), key=lambda p: str(p)):
            try:
                parts = path.relative_to(root).parts
                if any(part.startswith(".") or part in skip_dirs for part in parts[:-1]):
                    continue
                if path.is_file() and not path.name.startswith("."):
                    stat = path.stat()
                    sig.update(f"{path.name}:{stat.st_mtime}:{stat.st_size}".encode())
            except (ValueError, OSError):
                continue
    except OSError:
        pass

    return sig.hexdigest()[:24]


def extract_symbols_fallback(root: Path) -> list[dict[str, Any]]:
    """Fallback class and function parser for Python and JS/TS when graphify is not available."""
    symbols = []
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".forge",
        "graphify-out",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }

    py_class_re = re.compile(r"^class\s+([A-Za-z0-9_]+)")
    py_def_re = re.compile(r"^\s*def\s+([A-Za-z0-9_]+)")
    js_class_re = re.compile(r"^class\s+([A-Za-z0-9_]+)")
    js_func_re = re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z0-9_]+)")
    js_arrow_re = re.compile(r"^\s*const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>")

    try:
        for p in root.rglob("*"):
            try:
                parts = p.relative_to(root).parts
                if any(part.startswith(".") or part in skip_dirs for part in parts[:-1]):
                    continue
                if p.is_file() and not p.name.startswith("."):
                    rel_path = str(p.relative_to(root))
                    ext = p.suffix
                    if ext == ".py":
                        with open(p, encoding="utf-8", errors="replace") as f:
                            for idx, line in enumerate(f, 1):
                                m = py_class_re.match(line)
                                if m:
                                    symbols.append(
                                        {
                                            "name": m.group(1),
                                            "type": "class",
                                            "file": rel_path,
                                            "line": idx,
                                        }
                                    )
                                    continue
                                m = py_def_re.match(line)
                                if m:
                                    symbols.append(
                                        {
                                            "name": m.group(1),
                                            "type": "function",
                                            "file": rel_path,
                                            "line": idx,
                                        }
                                    )
                    elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                        with open(p, encoding="utf-8", errors="replace") as f:
                            for idx, line in enumerate(f, 1):
                                m = js_class_re.match(line)
                                if m:
                                    symbols.append(
                                        {
                                            "name": m.group(1),
                                            "type": "class",
                                            "file": rel_path,
                                            "line": idx,
                                        }
                                    )
                                    continue
                                m = js_func_re.match(line)
                                if m:
                                    symbols.append(
                                        {
                                            "name": m.group(1),
                                            "type": "function",
                                            "file": rel_path,
                                            "line": idx,
                                        }
                                    )
                                    continue
                                m = js_arrow_re.match(line)
                                if m:
                                    symbols.append(
                                        {
                                            "name": m.group(1),
                                            "type": "function",
                                            "file": rel_path,
                                            "line": idx,
                                        }
                                    )
            except Exception:
                continue
    except OSError:
        pass
    return symbols


def extract_dependencies_fallback(root: Path) -> list[dict[str, Any]]:
    """Fallback import statements parser for Python and JS/TS when graphify is not available."""
    dependencies = []
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".forge",
        "graphify-out",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }

    py_import_re = re.compile(
        r"^\s*(?:import\s+([A-Za-z0-9_.,\s]+)|from\s+([A-Za-z0-9_.]+)\s+import)"
    )
    js_import_re = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")
    js_require_re = re.compile(
        r"^\s*(?:const|let|var)\s+.*?\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    try:
        for p in root.rglob("*"):
            try:
                parts = p.relative_to(root).parts
                if any(part.startswith(".") or part in skip_dirs for part in parts[:-1]):
                    continue
                if p.is_file() and not p.name.startswith("."):
                    rel_path = str(p.relative_to(root))
                    ext = p.suffix
                    if ext == ".py":
                        with open(p, encoding="utf-8", errors="replace") as f:
                            for line in f:
                                m = py_import_re.match(line)
                                if m:
                                    dep = m.group(1) or m.group(2)
                                    dependencies.append(
                                        {
                                            "source": rel_path,
                                            "target": dep.strip(),
                                            "type": "import",
                                        }
                                    )
                    elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                        with open(p, encoding="utf-8", errors="replace") as f:
                            for line in f:
                                m = js_import_re.match(line)
                                if m:
                                    dependencies.append(
                                        {"source": rel_path, "target": m.group(1), "type": "import"}
                                    )
                                    continue
                                m = js_require_re.match(line)
                                if m:
                                    dependencies.append(
                                        {
                                            "source": rel_path,
                                            "target": m.group(1),
                                            "type": "require",
                                        }
                                    )
            except Exception:
                continue
    except OSError:
        pass
    return dependencies


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
        # 1. Scan/Optimize context
        prepared = prepare_runtime_sync(self.root, force=True, quiet=True)
        self.context_summary = prepared.context_summary
        self.context_file = str(prepared.context_file)

        # 2. Get list of files
        skip_dirs = {
            ".git",
            ".venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".forge",
            "graphify-out",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
        }
        self.files = []
        try:
            for p in sorted(self.root.rglob("*"), key=lambda x: str(x)):
                try:
                    parts = p.relative_to(self.root).parts
                    if any(part.startswith(".") or part in skip_dirs for part in parts[:-1]):
                        continue
                    if p.is_file() and not p.name.startswith("."):
                        stat = p.stat()
                        self.files.append(
                            {
                                "name": p.name,
                                "path": str(p.relative_to(self.root)),
                                "size_bytes": stat.st_size,
                                "mtime": stat.st_mtime,
                            }
                        )
                except (ValueError, OSError):
                    continue
        except OSError:
            pass

        # 3. Chunks
        chunker = Chunker(size=4000, overlap=200)
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

        # 4. Graph snapshot
        backend = GraphifyRepositoryGraph(root=self.root)
        self.graph_snapshot = None

        loop = asyncio.new_event_loop()
        try:
            is_graphify = loop.run_until_complete(backend.is_available())
            if is_graphify:
                active_provider = setup_graphify_credentials(self.root)
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
            self.symbols = extract_symbols_fallback(self.root)
            self.dependencies = extract_dependencies_fallback(self.root)

        # 5. Build summary markdown
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
def get_context(path: str | None = None) -> dict[str, Any]:
    w = get_watcher_for_path(path)
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


def is_daemon_running() -> bool:
    """Ping the daemon health endpoint to see if it is alive."""
    try:
        with httpx.Client(timeout=0.5) as client:
            r = client.get("http://127.0.0.1:16868/health")
            return r.status_code == 200
    except Exception:
        return False


def start_daemon_background() -> None:
    """Launch the daemon in the background as a subprocess."""
    import subprocess

    # Launch forgecli.cli.daemon in a background python process
    subprocess.Popen(
        [sys.executable, "-m", "forgecli.cli.daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def run_mcp_stdio() -> None:
    """Run the stdio MCP protocol handler, passing requests to the local daemon."""
    daemon_url = "http://127.0.0.1:16868"

    if not is_daemon_running():
        start_daemon_background()
        for _ in range(20):
            if is_daemon_running():
                break
            time.sleep(0.2)

    sys.stderr.write("Forge MCP Server active over stdio.\n")
    sys.stderr.flush()

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

                    content = ""
                    if tool_name == "get_summary":
                        r = client.get(f"{daemon_url}/summary?path={path_param}")
                        content = r.json()["markdown"]
                    elif tool_name == "get_optimized_context":
                        env_context = os.environ.get("FORGE_CONTEXT")
                        if env_context:
                            content = env_context
                        else:
                            r = client.get(f"{daemon_url}/context?path={path_param}")
                            content = r.json()["markdown"]
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
    # Start the daemon app on port 16868
    # Start watcher for the current directory by default
    get_watcher_for_path(Path.cwd())
    uvicorn.run(app, host="127.0.0.1", port=16868, log_level="warning")
