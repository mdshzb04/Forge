"""Disk-backed cache for prepared runtime context."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from forgecli.utils.paths import ProjectPaths

_CACHE_TTL_SECONDS = 3600.0


@dataclass(frozen=True)
class CachedRuntime:
    context_summary: str
    context_file: str
    node_count: int
    edge_count: int
    created_at: float


def _cache_dir() -> Path:
    path = ProjectPaths.from_env().cache_dir / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_fingerprint(root: Path) -> str:
    """Fingerprint a repo for cache invalidation (git HEAD + shallow layout)."""
    head = ""
    git_head = root / ".git" / "HEAD"
    if git_head.is_file():
        head = git_head.read_text(encoding="utf-8", errors="replace").strip()

    layout_sig = "0"
    try:
        names = sorted(p.name for p in root.iterdir() if not p.name.startswith("."))[:48]
        layout_sig = ",".join(names)
    except OSError:
        pass

    payload = f"{root.resolve()}|{head}|{layout_sig}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def load_runtime_cache(fingerprint: str) -> CachedRuntime | None:
    path = _cache_dir() / f"{fingerprint}.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        created_at = float(payload.get("created_at", 0))
        if time.time() - created_at > _CACHE_TTL_SECONDS:
            path.unlink(missing_ok=True)
            return None
        context_file = Path(str(payload["context_file"]))
        if not context_file.is_file():
            return None
        return CachedRuntime(
            context_summary=str(payload["context_summary"]),
            context_file=str(context_file),
            node_count=int(payload.get("node_count", 0)),
            edge_count=int(payload.get("edge_count", 0)),
            created_at=created_at,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def save_runtime_cache(fingerprint: str, runtime: CachedRuntime) -> None:
    path = _cache_dir() / f"{fingerprint}.json"
    path.write_text(json.dumps(asdict(runtime), indent=2), encoding="utf-8")
