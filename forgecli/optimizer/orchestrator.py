"""Complete Context and Token Optimization Runtime Orchestrator.

Integrates budget config, git state, semantic ranking, dependency-based early-stop
retrieval, AST pruning, and compression to build the ultimate query-specific context.
"""



from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from forgecli.optimizer.adaptive_budget import AdaptiveContextBudget
from forgecli.optimizer.ast_extractor import ASTExtractor
from forgecli.optimizer.cache import ContextCache
from forgecli.optimizer.compression import ContextCompressionEngine
from forgecli.optimizer.cost_estimator import TokenCostEstimator
from forgecli.optimizer.git_context import GitContextManager
from forgecli.optimizer.intelligent_retrieval import IntelligentRetrievalManager
from forgecli.optimizer.quality_validation import QualityValidator
from forgecli.optimizer.semantic_ranking import SemanticRanker

logger = logging.getLogger(__name__)





class OptimizationRuntimeOrchestrator:

    """Orchestrates all token optimization sub-systems to generate high-fidelity, minimized context."""



    def __init__(self, repo_root: Path, settings: Any = None) -> None:
        self.root = Path(repo_root).resolve()
        from forgecli.config.settings import ForgeSettings
        self.settings = settings or ForgeSettings()

        cache_dir = self.root / ".forge"
        cache_dir.mkdir(exist_ok=True)
        self.cache = ContextCache(cache_dir / "context_cache.db")
        self.git_manager = GitContextManager(self.root)
        self.compressor = ContextCompressionEngine()
        self.estimator = TokenCostEstimator()

        from forgecli.optimizer.retrieval_cache import RetrievalCache
        self.retrieval_cache = RetrievalCache(
            cache_dir / "retrieval_cache.db",
            ttl_seconds=getattr(self.settings.optimizer, "retrieval_cache_ttl", 3600.0)
        )



    def get_query_optimized_context(

        self,

        query: str,

        files: list[dict[str, Any]],

        symbols: list[dict[str, Any]],

        dependencies: list[dict[str, Any]],

        model_name: str = "claude-3-5-sonnet",


    ) -> str:

        """Run the complete 12-tier context optimization pipeline for the query."""

        try:

            budget = AdaptiveContextBudget.get_budget_config(model_name)

            target_context_tokens = budget["target_context"]

            # Compute recursive fingerprint for cache validation
            from forgecli.cli.daemon import get_recursive_fingerprint
            from forgecli.runtime.cache_store import repo_fingerprint
            try:
                fingerprint = get_recursive_fingerprint(self.root)
            except Exception:
                fingerprint = repo_fingerprint(self.root)

            git_modified = self.git_manager.get_modified_files()

            git_summary = self.git_manager.get_git_summary()

            # Instantiate retrieval manager with cache and fingerprint
            retrieval_mgr = IntelligentRetrievalManager(
                self.root, dependencies, symbols, cache=self.retrieval_cache, fingerprint=fingerprint
            )

            # Check semantic search cache
            cache_key_ir = f"semantic_search:{query}"
            cached_mapping = self.retrieval_cache.get("semantic_search", cache_key_ir, fingerprint)
            if cached_mapping is not None:
                needed_mapping = {k: set(v) for k, v in cached_mapping.items()}
            else:
                needed_mapping = retrieval_mgr.retrieve_context_for_query(query)
                serialized_mapping = {k: list(v) for k, v in needed_mapping.items()}
                self.retrieval_cache.set("semantic_search", cache_key_ir, serialized_mapping, fingerprint)

            file_paths = [self.root / f["path"] for f in files if (self.root / f["path"]).exists()]

            ranker = SemanticRanker(self.root)

            # Check ranked files cache
            cache_key_rank = f"ranked_files:{query}"
            cached_ranked = self.retrieval_cache.get("ranked_files", cache_key_rank, fingerprint)
            if cached_ranked is not None:
                ranked_files = [(Path(self.root / item[0]), item[1]) for item in cached_ranked]
            else:
                ranked_files = ranker.rank_files(query, file_paths, dependencies, top_n=20)
                serialized_ranked = [(str(Path(p).relative_to(self.root)), score) for p, score in ranked_files]
                self.retrieval_cache.set("ranked_files", cache_key_rank, serialized_ranked, fingerprint)

            context_blocks = []

            current_tokens = 0

            if git_summary:

                context_blocks.append(git_summary)

                current_tokens += self.estimator.estimate_tokens(git_summary)

            seen_files = set()

            # Set up comment stripping configuration
            import re
            comment_mode = getattr(self.settings.optimizer, "comment_stripping", "off")
            if re.search(r"\b(?:preserve|keep|do not strip|do not remove|dont strip)\b.*\bcomments?\b", query, re.IGNORECASE):
                comment_mode = "off"

            for path, _rank_score in ranked_files:

                if current_tokens >= target_context_tokens:

                    break

                rel_path = str(path.relative_to(self.root))

                seen_files.add(rel_path)

                self.cache.get_file_ast(path)

                keep_names = needed_mapping.get(rel_path, set())

                if not keep_names:

                    keep_names = {s["name"] for s in symbols if s["file"] == rel_path}

                pruned_code = ASTExtractor.prune_file(path, keep_names)

                if (path.suffix == ".py" and not QualityValidator.validate_python_syntax(pruned_code)) or (path.suffix in (".js", ".ts", ".jsx", ".tsx", ".go", ".rs") and not QualityValidator.validate_braces_balance(pruned_code)):

                    pruned_code = path.read_text(encoding="utf-8", errors="replace")

                # Apply comment stripping if active
                if comment_mode != "off":
                    from forgecli.optimizer.comment_stripper import CommentStripper
                    pruned_code = CommentStripper.strip_comments(pruned_code, filepath=str(path), mode=comment_mode)

                self.cache.set_file_ast(path, [{"content": pruned_code}])

                block = f"### File: {rel_path}\n```\n{pruned_code}\n```"

                context_blocks.append(block)

                current_tokens += self.estimator.estimate_tokens(block)

            for m_file in git_modified:

                if current_tokens >= target_context_tokens:

                    break

                if m_file in seen_files:

                    continue

                full_path = self.root / m_file

                if full_path.exists() and full_path.is_file():

                    pruned_code = ASTExtractor.prune_file(full_path, set())

                    # Apply comment stripping to modified files
                    if comment_mode != "off":
                        from forgecli.optimizer.comment_stripper import CommentStripper
                        pruned_code = CommentStripper.strip_comments(pruned_code, filepath=str(full_path), mode=comment_mode)

                    block = f"### File: {m_file} (Modified)\n```\n{pruned_code}\n```"

                    context_blocks.append(block)

                    current_tokens += self.estimator.estimate_tokens(block)





            raw_assembled = "\n\n".join(context_blocks)

            compressed_context = self.compressor.compress_all(raw_assembled)





            final_tokens = self.estimator.estimate_tokens(compressed_context)

            est_cost = self.estimator.estimate_cost(model_name, final_tokens, 500)

            est_latency = self.estimator.estimate_latency(model_name, final_tokens, 500)





            header = (

                "=== OPTIMIZED CONTEXT SUMMARY ===\n"

                f"- Model Config: {model_name} (Reasoning: {budget['is_reasoning_model']})\n"

                f"- Input Token Estimate: {final_tokens} / {target_context_tokens}\n"

                f"- Estimated Call Cost: ${est_cost:.4f} USD\n"

                f"- Expected Latency: {est_latency:.1f}s\n"

                "=================================\n\n"

            )



            return header + compressed_context



        except Exception as e:

            logger.error(f"Error executing context optimization orchestrator: {e}", exc_info=True)



            return "### Fallback Context\nError building optimized context."

