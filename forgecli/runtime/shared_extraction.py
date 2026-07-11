"""Canonical repository extraction — symbol indexing, dependency parsing, file scanning.

This is the single source of truth used by both the daemon and prepare_runtime_sync.
All other implementations (middleware defaults, inline daemon parsers) must delegate here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", ".venv", "__pycache__", "node_modules", "dist", "build",
    ".forge", "forgegraph-out", ".mypy_cache", ".pytest_cache", ".ruff_cache",
})

_SUPPORTED_EXTS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
    ".rb", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".scala",
})

_PY_CLASS_RE = re.compile(r"^class\s+([A-Za-z0-9_]+)")
_PY_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z0-9_]+)")
_PY_IMPORT_RE = re.compile(r"^\s*(?:import\s+([A-Za-z0-9_.,\s]+)|from\s+([A-Za-z0-9_.]+)\s+import)")

_JS_CLASS_RE = re.compile(r"^class\s+([A-Za-z0-9_]+)")
_JS_FUNC_RE = re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z0-9_]+)")
_JS_ARROW_RE = re.compile(r"^\s*const\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>")
_JS_IMPORT_RE = re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")
_JS_REQUIRE_RE = re.compile(r"^\s*(?:const|let|var)\s+.*?\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)")


def should_skip(parts: tuple[str, ...]) -> bool:
    return any(part.startswith(".") or part in _SKIP_DIRS for part in parts[:-1])


def iter_trackable_files(root: Path) -> Iterable[Path]:
    root = root.resolve()
    try:
        for p in root.rglob("*"):
            try:
                parts = p.relative_to(root).parts
                if should_skip(parts):
                    continue
                if p.is_file() and not p.name.startswith("."):
                    yield p
            except (ValueError, OSError):
                continue
    except OSError:
        return


def extract_symbols(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    files_to_parse = list(iter_trackable_files(root))

    def parse_file(p: Path) -> list[dict[str, Any]]:
        file_syms: list[dict[str, Any]] = []
        rel_path = str(p.relative_to(root))
        ext = p.suffix
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for idx, line in enumerate(f, 1):
                    if ext == ".py":
                        m = _PY_CLASS_RE.match(line)
                        if m:
                            file_syms.append({"name": m.group(1), "type": "class", "file": rel_path, "line": idx})
                            continue
                        m = _PY_DEF_RE.match(line)
                        if m:
                            file_syms.append({"name": m.group(1), "type": "function", "file": rel_path, "line": idx})
                    elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                        m = _JS_CLASS_RE.match(line)
                        if m:
                            file_syms.append({"name": m.group(1), "type": "class", "file": rel_path, "line": idx})
                            continue
                        m = _JS_FUNC_RE.match(line)
                        if m:
                            file_syms.append({"name": m.group(1), "type": "function", "file": rel_path, "line": idx})
                            continue
                        m = _JS_ARROW_RE.match(line)
                        if m:
                            file_syms.append({"name": m.group(1), "type": "function", "file": rel_path, "line": idx})
        except Exception:
            pass
        return file_syms

    symbols: list[dict[str, Any]] = []
    with ThreadPoolExecutor() as executor:
        for result in executor.map(parse_file, files_to_parse):
            symbols.extend(result)
    return symbols


def extract_dependencies(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    files_to_parse = list(iter_trackable_files(root))

    def parse_file(p: Path) -> list[dict[str, Any]]:
        file_deps: list[dict[str, Any]] = []
        rel_path = str(p.relative_to(root))
        ext = p.suffix
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if ext == ".py":
                        m = _PY_IMPORT_RE.match(line)
                        if m:
                            dep = m.group(1) or m.group(2)
                            file_deps.append({"source": rel_path, "target": dep.strip(), "type": "import"})
                    elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                        m = _JS_IMPORT_RE.match(line)
                        if m:
                            file_deps.append({"source": rel_path, "target": m.group(1), "type": "import"})
                            continue
                        m = _JS_REQUIRE_RE.match(line)
                        if m:
                            file_deps.append({"source": rel_path, "target": m.group(1), "type": "require"})
        except Exception:
            pass
        return file_deps

    dependencies: list[dict[str, Any]] = []
    with ThreadPoolExecutor() as executor:
        for result in executor.map(parse_file, files_to_parse):
            dependencies.extend(result)
    return dependencies


def extract_files(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    try:
        for p in sorted(root.rglob("*"), key=lambda x: str(x)):
            try:
                parts = p.relative_to(root).parts
                if should_skip(parts):
                    continue
                if p.is_file() and not p.name.startswith("."):
                    stat = p.stat()
                    files.append({
                        "name": p.name,
                        "path": str(p.relative_to(root)),
                        "size_bytes": stat.st_size,
                        "mtime": stat.st_mtime,
                    })
            except (ValueError, OSError):
                continue
    except OSError:
        pass
    return files


def repo_size_tier(root: Path) -> tuple[int, str]:
    count = 0
    stack = [root]
    while stack and count <= 800:
        current = stack.pop()
        try:
            for entry in current.iterdir():
                if entry.name in _SKIP_DIRS or entry.name.startswith("."):
                    continue
                count += 1
                if count > 800:
                    break
                if entry.is_dir():
                    stack.append(entry)
        except OSError:
            continue
    if count == 0:
        return count, "empty"
    if count > 400:
        return count, "heavy"
    return count, "normal"
