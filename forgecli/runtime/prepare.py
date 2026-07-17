"""Fast repository context for AI wrapper commands.

Unified context preparation path used by all wrappers and the daemon.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from forgecli.runtime.cache_store import (
    CachedRuntime,
    load_runtime_cache,
    repo_fingerprint,
    save_runtime_cache,
)
from forgecli.runtime.shared_extraction import (
    extract_dependencies,
    extract_files,
    extract_symbols,
    repo_size_tier,
)
from forgecli.utils.paths import ProjectPaths


@dataclass(frozen=True)
class PreparedRuntime:
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


def _scan_repo_structure(root: Path) -> str:
    _entry_count, tier = repo_size_tier(root)
    lines = [f"Repository: {root.name}", f"Root: {root}"]
    git_info = _git_line(root)
    if git_info:
        lines.append(git_info)

    if tier == "empty":
        lines.extend(["", "Empty repository — no source files yet."])
        return "\n".join(lines)

    graph_marker = root / "forgegraph-out" / "graph.json"
    if graph_marker.is_file():
        lines.append("")
        lines.append("Knowledge graph available at forgegraph-out/.")

    return "\n".join(lines)


def _build_enriched_context(root: Path) -> str:
    """Build context using AST extraction, semantic ranking, and compression."""
    files = extract_files(root)
    symbols = extract_symbols(root)
    dependencies = extract_dependencies(root)

    file_paths = [root / f["path"] for f in files if (root / f["path"]).exists()]

    from forgecli.optimizer.compression import ContextCompressionEngine
    compressor = ContextCompressionEngine()

    from forgecli.optimizer.cost_estimator import TokenCostEstimator
    estimator = TokenCostEstimator()

    target_tokens = 8_000

    from forgecli.optimizer.semantic_ranking import SemanticRanker
    ranker = SemanticRanker(root)
    ranked = ranker.rank_files(query="", files=file_paths, dependencies=dependencies, top_n=25)

    from forgecli.optimizer.ast_extractor import ASTExtractor
    from forgecli.optimizer.git_context import GitContextManager
    from forgecli.optimizer.quality_validation import QualityValidator
    git_manager = GitContextManager(root)

    blocks: list[str] = []
    current_tokens = 0

    structure = _scan_repo_structure(root)
    blocks.append(structure)
    current_tokens += estimator.estimate_tokens(structure)

    git_summary = git_manager.get_git_summary()
    if git_summary:
        git_tokens = estimator.estimate_tokens(git_summary)
        if current_tokens + git_tokens < target_tokens:
            blocks.append(git_summary)
            current_tokens += git_tokens

    for path, _score in ranked:
        if current_tokens >= target_tokens:
            break
        rel_path = str(path.relative_to(root))
        try:
            keep_names = {s["name"] for s in symbols if s["file"] == rel_path}
            pruned = ASTExtractor.prune_file(path, keep_names) if keep_names else path.read_text(encoding="utf-8", errors="replace")
            if (path.suffix == ".py" and not QualityValidator.validate_python_syntax(pruned)) or (path.suffix in (".js", ".ts", ".jsx", ".tsx", ".go", ".rs") and not QualityValidator.validate_braces_balance(pruned)):
                pruned = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pruned = path.read_text(encoding="utf-8", errors="replace")

        block = f"### File: {rel_path}\n```\n{pruned}\n```"
        block_tokens = estimator.estimate_tokens(block)
        if current_tokens + block_tokens > target_tokens:
            break
        blocks.append(block)
        current_tokens += block_tokens

    raw = "\n\n".join(blocks)
    return compressor.compress_all(raw)


def get_promptforge_instructions(settings) -> str:
    from forgecli.optimizer.promptforge import Intensity
    from forgecli.optimizer.promptforge.ruleset import _INTENSITY_GUIDANCE
    enabled = settings.prompt_optimizer.enabled
    intensity_str = settings.prompt_optimizer.intensity
    if not enabled or intensity_str == "off":
        return ""
    try:
        intensity = Intensity.parse(intensity_str)
    except ValueError:
        intensity = Intensity.LITE
    return _INTENSITY_GUIDANCE.get(intensity, "")




def get_loop_engineering_instructions(settings) -> str:
    loop = getattr(settings, "loop_engineering", None)
    if loop is None:
        return ""
    if not loop.enabled:
        return ""
    lines = [
        "Loop engineering policy:",
        f"- Pattern: {loop.pattern}",
        f"- Claude Code budget: {loop.budget_currency} {loop.claude_usd_limit:.2f}",
        f"- Cursor budget: {loop.budget_currency} {loop.cursor_usd_limit:.2f}",
        f"- Codex budget: {loop.budget_currency} {loop.codex_usd_limit:.2f}",
        f"- Antigravity budget: {loop.budget_currency} {loop.antigravity_usd_limit:.2f}",
    ]
    if loop.enforce_low_token_mode:
        lines.append("- Prefer low-token edits, compact diffs, and narrow context.")
    return "\n".join(lines)


def get_responseforge_instructions(settings) -> str:
    from forgecli.optimizer.responseforge import ResponseForgeIntensity
    from forgecli.optimizer.responseforge.ruleset import _CAVEMAN_GUIDANCE
    enabled = settings.responseforge.enabled
    intensity_str = settings.responseforge.intensity
    if not enabled or intensity_str == "off":
        return ""
    try:
        intensity = ResponseForgeIntensity.parse(intensity_str)
    except ValueError:
        intensity = ResponseForgeIntensity.LITE
    return _CAVEMAN_GUIDANCE.get(intensity, "")


def build_merged_context(repo_context: str, repo_root: Path | None = None) -> str:
    from forgecli.config.loader import ConfigLoader
    try:
        settings = ConfigLoader().load()
    except Exception:
        from forgecli.config.settings import ForgeSettings
        settings = ForgeSettings()

    promptforge_guidance = get_promptforge_instructions(settings)
    responseforge_guidance = get_responseforge_instructions(settings)
    loop_guidance = get_loop_engineering_instructions(settings)

    blocks = []
    if promptforge_guidance:
        blocks.append(
            "=== SYSTEM INSTRUCTION: IMPLEMENTATION STYLE (PONYTAIL) ===\n"
            f"{promptforge_guidance}\n"
            "==========================================================="
        )
    if responseforge_guidance:
        blocks.append(
            "=== SYSTEM INSTRUCTION: RESPOND STYLE (CAVEMAN) ===\n"
            f"{responseforge_guidance}\n"
            "==================================================="
        )
    if loop_guidance:
        blocks.append(
            "=== SYSTEM INSTRUCTION: LOOP ENGINEERING POLICY ===\n"
            f"{loop_guidance}\n"
            "==================================================="
        )

    instructions = "\n\n".join(blocks) + "\n\n" if blocks else ""
    return instructions + repo_context


def prepare_runtime_sync(
    start: Path,
    *,
    force: bool = False,
    quiet: bool = False,
) -> PreparedRuntime:
    root = resolve_repo_root(start)
    fingerprint = repo_fingerprint(root)

    if not force:
        cached = load_runtime_cache(fingerprint)
        if cached is not None:
            return PreparedRuntime.from_cached(root, cached)

    enriched = _build_enriched_context(root)

    cache_dir = ProjectPaths.from_env().cache_dir / "runtime" / "context"
    cache_dir.mkdir(parents=True, exist_ok=True)
    context_file = cache_dir / f"{fingerprint}.md"
    context_file.write_text(enriched, encoding="utf-8")

    save_runtime_cache(
        fingerprint,
        CachedRuntime(
            context_summary=enriched,
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
        context_summary=enriched,
        context_file=context_file,
        from_cache=False,
    )


def build_behavior_instructions() -> str:
    """Return behavior instructions block only (no repo context)."""
    return build_merged_context(repo_context="")


def get_merged_context(repo_context: str) -> str:
    """[deprecated] Use build_merged_context instead."""
    return build_merged_context(repo_context=repo_context)
