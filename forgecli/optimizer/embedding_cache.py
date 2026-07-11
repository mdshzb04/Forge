"""SQLite-backed, thread-safe Embedding Cache.

Caches vector embeddings based on file/input hash, model name, and embedding version.
Supports incremental updates to only fetch missing embeddings.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path


class EmbeddingCache:
    """Thread-safe SQLite cache for vector embeddings with incremental lookup."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the embedding cache table if it does not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_cache (
                        model TEXT NOT NULL,
                        input_hash TEXT NOT NULL,
                        vector TEXT NOT NULL,
                        version TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (model, input_hash, version)
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def _hash_input(self, text: str) -> str:
        """Compute SHA256 hash of input text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def lookup(
        self, model: str, inputs: list[str], version: str = "v1"
    ) -> tuple[dict[str, list[float]], list[str]]:
        """Look up embeddings for a list of inputs.

        Returns:
            A tuple of (cached_embeddings, missing_inputs), where:
              - cached_embeddings: dict mapping input string -> list of floats
              - missing_inputs: subset of inputs that were not cached
        """
        if not inputs:
            return {}, []

        cached_embeddings = {}
        missing_inputs = []
        hash_to_input = {self._hash_input(inp): inp for inp in inputs}
        hashes = list(hash_to_input.keys())

        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                # Query in chunks to avoid SQLite parameter limit (999)
                chunk_size = 500
                for i in range(0, len(hashes), chunk_size):
                    chunk_hashes = hashes[i : i + chunk_size]
                    placeholders = ",".join("?" for _ in chunk_hashes)
                    query = f"""
                        SELECT input_hash, vector FROM embedding_cache
                        WHERE model = ? AND version = ? AND input_hash IN ({placeholders})
                    """
                    cursor.execute(query, [model, version] + chunk_hashes)
                    for row in cursor.fetchall():
                        h, vec_json = row
                        original_input = hash_to_input.get(h)
                        if original_input is not None:
                            cached_embeddings[original_input] = json.loads(vec_json)
            except Exception:
                pass
            finally:
                conn.close()

        # Identify missing inputs
        for inp in inputs:
            if inp not in cached_embeddings:
                missing_inputs.append(inp)

        return cached_embeddings, missing_inputs

    def save(self, model: str, embeddings: dict[str, list[float]], version: str = "v1") -> None:
        """Save a dictionary of input -> vector embeddings to the cache."""
        if not embeddings:
            return

        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                created_at = time.time()
                # Insert in batches
                batch = []
                for inp, vector in embeddings.items():
                    h = self._hash_input(inp)
                    batch.append((model, h, json.dumps(vector), version, created_at))

                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO embedding_cache (model, input_hash, vector, version, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    batch
                )
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()

    def clear(self) -> None:
        """Clear all cached embeddings."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM embedding_cache")
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()
