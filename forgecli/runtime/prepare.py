"""Fast repository context for AI wrapper commands — no full codebase indexing."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from forgecli.optimizer.optimizer import ContextOptimizer
from forgecli.runtime.cache_store import (
    CachedRuntime,
    load_runtime_cache,
    repo_fingerprint,
    save_runtime_cache,
)
from forgecli.utils.paths import ProjectPaths

_SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".forge",
    "forgegraph-out",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


@dataclass(frozen=True)
class PreparedRuntime:
    """Optimized repository context ready for a wrapper CLI."""

    root: Path
    context_summary: str
    context_file: Path
    from_cache: bool

    @classmethod
    def from_cached(cls, root: Path, cached: CachedRuntime) -> PreparedRuntime:
        return cls(
            root=root,
            context_summary=cached.context_summary,
            context_file=Path(cached.context_file),
            from_cache=True,
        )


def resolve_repo_root(start: Path) -> Path:
    """Return the nearest git repository root, or ``start`` when not in a repo."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _git_line(root: Path) -> str | None:
    from forgecli.platform.shell import run

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    if branch.ok and branch.stdout.strip():
        return f"Branch: {branch.stdout.strip()}"
    return None


def _repo_scale(root: Path) -> tuple[int, str]:
    """Roughly size the repo and classify it as empty / normal / heavy.

    Counts entries breadth-first with a hard cap so this stays O(1)-ish even on
    huge trees. Returns ``(entry_count, tier)`` where tier is one of
    ``"empty"``, ``"normal"``, ``"heavy"``.
    """
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


def _scan_repo_light(root: Path) -> str:
    """Build a small repo snapshot without indexing the full codebase.

    The scan breadth adapts to repo size: empty repos still yield a valid,
    non-blank context (so behavior instructions always apply); heavy repos get
    a wider-but-still-bounded snapshot and hand deeper compression to the
    optimizer, plus a pointer to the full knowledge graph.
    """
    entry_count, tier = _repo_scale(root)

    lines = [
        f"Repository: {root.name}",
        f"Root: {root}",
    ]
    git_info = _git_line(root)
    if git_info:
        lines.append(git_info)

    if tier == "empty":
        lines.extend(
            [
                "",
                "Empty repository — no source files yet.",
                "No project layout to summarize; optimization applies to prompts only.",
            ]
        )
        return "\n".join(lines)

    top_cap = 60 if tier == "heavy" else 36
    child_cap = 4 if tier == "heavy" else 6
    layout_cap = 120 if tier == "heavy" else 72

    layout: list[str] = []
    try:
        for entry in sorted(root.iterdir(), key=lambda p: p.name.lower())[:top_cap]:
            if entry.name in _SKIP_DIRS or entry.name.startswith("."):
                continue
            if entry.is_dir():
                layout.append(f"{entry.name}/")
                try:
                    for child in sorted(entry.iterdir(), key=lambda p: p.name.lower())[:child_cap]:
                        if child.name in _SKIP_DIRS or child.name.startswith("."):
                            continue
                        suffix = "/" if child.is_dir() else ""
                        layout.append(f"  {child.name}{suffix}")
                except OSError:
                    pass
            else:
                layout.append(entry.name)
    except OSError:
        pass

    if layout:
        lines.extend(["", "Project layout (shallow scan):", *layout[:layout_cap]])

    if tier == "heavy":
        lines.append("")
        lines.append(
            f"Large repository (~{entry_count}+ entries). Context is aggressively "
            "compressed; run `forge graph build` for a full symbol index."
        )

    graph_marker = root / "forgegraph-out" / "graph.json"
    if graph_marker.is_file():
        lines.append("")
        lines.append(
            "Knowledge graph already on disk at forgegraph-out/. "
            "Run `forge graph build` separately when you want a full refresh."
        )

    return "\n".join(lines)


def _optimize_tokens(text: str) -> str:
    # Compress harder as the raw context grows so heavy repos stay bounded.
    max_tokens = 8_000 if len(text) <= 6_000 else 4_000
    optimizer = ContextOptimizer(max_context_tokens=max_tokens)
    result = optimizer.optimize(text)
    if not result.chunks:
        return text[:12_000]
    merged = "\n".join(chunk.text for chunk in result.chunks[:24])
    return merged[:12_000]


def get_ponytail_instructions(settings) -> str:
    from forgecli.optimizer.ponytail import Intensity
    from forgecli.optimizer.ponytail.ruleset import _INTENSITY_GUIDANCE

    enabled = settings.prompt_optimizer.enabled
    intensity_str = settings.prompt_optimizer.intensity
    if not enabled or intensity_str == "off":
        return ""

    try:
        intensity = Intensity.parse(intensity_str)
    except ValueError:
        intensity = Intensity.LITE

    return _INTENSITY_GUIDANCE.get(intensity, "")


def get_caveman_instructions(settings) -> str:
    from forgecli.optimizer.caveman import CavemanIntensity
    from forgecli.optimizer.caveman.ruleset import _CAVEMAN_GUIDANCE

    enabled = settings.caveman.enabled
    intensity_str = settings.caveman.intensity
    if not enabled or intensity_str == "off":
        return ""

    try:
        intensity = CavemanIntensity.parse(intensity_str)
    except ValueError:
        intensity = CavemanIntensity.LITE

    return _CAVEMAN_GUIDANCE.get(intensity, "")


def build_behavior_instructions() -> str:
    from forgecli.config.loader import ConfigLoader

    try:
        settings = ConfigLoader().load()
    except Exception:
        from forgecli.config.settings import ForgeSettings

        settings = ForgeSettings()

    ponytail_guidance = get_ponytail_instructions(settings)
    caveman_guidance = get_caveman_instructions(settings)

    blocks = []
    if ponytail_guidance:
        blocks.append(
            "=== SYSTEM INSTRUCTION: IMPLEMENTATION STYLE (PONYTAIL) ===\n"
            f"{ponytail_guidance}\n"
            "==========================================================="
        )
    if caveman_guidance:
        blocks.append(
            "=== SYSTEM INSTRUCTION: RESPOND STYLE (CAVEMAN) ===\n"
            f"{caveman_guidance}\n"
            "==================================================="
        )
    if blocks:
        return "\n\n".join(blocks) + "\n\n"
    return ""


def get_merged_context(repo_context: str) -> str:
    instructions = build_behavior_instructions()
    return instructions + repo_context


def prepare_runtime_sync(
    start: Path,
    *,
    force: bool = False,
    quiet: bool = False,
) -> PreparedRuntime:
    """Prepare lightweight optimized context — no full graph build."""
    root = resolve_repo_root(start)
    fingerprint = repo_fingerprint(root)

    if not force:
        cached = load_runtime_cache(fingerprint)
        if cached is not None:
            return PreparedRuntime.from_cached(root, cached)

    raw_context = _scan_repo_light(root)
    # Repository context is strictly limited to summaries, relevant files, layout, dependency info etc.
    token_optimized = _optimize_tokens(raw_context)

    # Optimization pipeline check: never allow optimized context to be larger than raw context
    if len(token_optimized) > len(raw_context):
        token_optimized = raw_context

    cache_dir = ProjectPaths.from_env().cache_dir / "runtime" / "context"
    cache_dir.mkdir(parents=True, exist_ok=True)
    context_file = cache_dir / f"{fingerprint}.md"
    context_file.write_text(token_optimized, encoding="utf-8")

    save_runtime_cache(
        fingerprint,
        CachedRuntime(
            context_summary=token_optimized,
            context_file=str(context_file),
            node_count=0,
            edge_count=0,
            created_at=time.time(),
        ),
    )

    if not quiet:
        from forgecli.cli.ui import info

        info(f"Optimized context for [accent]{root.name}[/accent] (cached for reuse)")

    return PreparedRuntime(
        root=root,
        context_summary=token_optimized,
        context_file=context_file,
        from_cache=False,
    )
