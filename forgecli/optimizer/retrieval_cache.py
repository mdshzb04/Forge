"""SQLite-backed, thread-safe Retrieval Cache.

Caches semantic searches, ranked files, dependency traversals, symbol lookups,
and graph traversals. Invalidates automatically when repository state changes
or TTL expires.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class RetrievalCache:
    """Thread-safe SQLite cache for retrieval results with automatic fingerprint invalidation."""

    def __init__(self, db_path: Path, ttl_seconds: float = 3600.0) -> None:
        self.db_path = Path(db_path).resolve()
        self.ttl = ttl_seconds
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the cache database and tables if they do not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS retrieval_cache (
                        category TEXT NOT NULL,
                        cache_key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (category, cache_key)
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def get(self, category: str, key: str, current_fingerprint: str) -> Any | None:
        """Retrieve value if it exists, is unexpired, and matches the fingerprint."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value, fingerprint, created_at FROM retrieval_cache WHERE category = ? AND cache_key = ?",
                    (category, key)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                value_json, cached_fingerprint, created_at = row

                # Check fingerprint match
                if cached_fingerprint != current_fingerprint:
                    # Invalidate stale entry
                    cursor.execute(
                        "DELETE FROM retrieval_cache WHERE category = ? AND cache_key = ?",
                        (category, key)
                    )
                    conn.commit()
                    return None

                # Check TTL expiration
                if time.time() - created_at > self.ttl:
                    # Invalidate expired entry
                    cursor.execute(
                        "DELETE FROM retrieval_cache WHERE category = ? AND cache_key = ?",
                        (category, key)
                    )
                    conn.commit()
                    return None

                return json.loads(value_json)
            except Exception:
                return None
            finally:
                conn.close()

    def set(self, category: str, key: str, value: Any, current_fingerprint: str) -> None:
        """Insert or update a cache entry."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO retrieval_cache (category, cache_key, value, fingerprint, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (category, key, json.dumps(value), current_fingerprint, time.time())
                )
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()

    def clear(self) -> None:
        """Clear all cached entries."""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM retrieval_cache")
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()
