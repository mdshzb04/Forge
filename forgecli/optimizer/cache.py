"""SQLite-backed Context Cache.

Caches codebase file states, extracted AST nodes, and dependency links
to avoid repetitive parsing and repository scans.
"""



from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ContextCache:

    """Persistent context cache powered by a local SQLite database."""



    def __init__(self, cache_db_path: Path) -> None:

        self.db_path = Path(cache_db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: sqlite3.Connection | None = None

        self._init_db()



    def _init_db(self) -> None:

        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)

        self._conn.row_factory = sqlite3.Row

        with self._conn:



            self._conn.execute(

                """
                CREATE TABLE IF NOT EXISTS file_ast_cache (
                    filepath TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL,
                    ast_data TEXT NOT NULL
                )
                """

            )



            self._conn.execute(

                """
                CREATE TABLE IF NOT EXISTS dependency_cache (
                    repo_path TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    dependencies TEXT NOT NULL,
                    symbols TEXT NOT NULL
                )
                """

            )



    def close(self) -> None:

        if self._conn:

            self._conn.close()

            self._conn = None



    def get_file_ast(self, filepath: Path) -> list[dict[str, Any]] | None:

        """Fetch cached AST details if the file has not changed in mtime/size."""

        if not filepath.exists():

            return None

        stat = filepath.stat()

        rel_path = str(filepath)



        cursor = self._conn.execute(

            "SELECT ast_data FROM file_ast_cache WHERE filepath = ? AND mtime = ? AND size = ?",

            (rel_path, stat.st_mtime, stat.st_size),

        )

        row = cursor.fetchone()

        if row:

            try:

                return json.loads(row["ast_data"])

            except Exception:

                pass

        return None



    def set_file_ast(self, filepath: Path, ast_nodes: list[Any]) -> None:

        """Cache the serialized AST nodes for a file."""

        if not filepath.exists():

            return

        stat = filepath.stat()

        rel_path = str(filepath)

        ast_json = json.dumps(ast_nodes)



        with self._conn:

            self._conn.execute(

                """
                INSERT OR REPLACE INTO file_ast_cache (filepath, mtime, size, ast_data)
                VALUES (?, ?, ?, ?)
                """,

                (rel_path, stat.st_mtime, stat.st_size, ast_json),

            )



    def get_repo_metadata(self, repo_path: Path, fingerprint: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:

        """Fetch cached dependencies and symbols for a repository if fingerprint matches."""

        cursor = self._conn.execute(

            "SELECT dependencies, symbols FROM dependency_cache WHERE repo_path = ? AND fingerprint = ?",

            (str(repo_path), fingerprint),

        )

        row = cursor.fetchone()

        if row:

            try:

                deps = json.loads(row["dependencies"])

                syms = json.loads(row["symbols"])

                return deps, syms

            except Exception:

                pass

        return None



    def set_repo_metadata(self, repo_path: Path, fingerprint: str, dependencies: list[Any], symbols: list[Any]) -> None:

        """Cache dependencies and symbols metadata."""

        deps_json = json.dumps(dependencies)

        syms_json = json.dumps(symbols)



        with self._conn:

            self._conn.execute(

                """
                INSERT OR REPLACE INTO dependency_cache (repo_path, fingerprint, dependencies, symbols)
                VALUES (?, ?, ?, ?)
                """,

                (str(repo_path), fingerprint, deps_json, syms_json),

            )

