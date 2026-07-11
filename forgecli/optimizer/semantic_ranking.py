"""Semantic Ranking Engine.

Ranks files by matching relevance scores against user queries, combining
lexical overlap with import dependency centrality.
"""



from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


class SemanticRanker:

    """Ranks codebase files using a combination of TF-IDF query overlap and centrality."""



    def __init__(self, repo_root: Path) -> None:

        self.root = Path(repo_root).resolve()



    def rank_files(
        self,
        query: str,
        files: list[Path],
        dependencies: list[dict[str, str]],
        top_n: int = 10,
    ) -> list[tuple[Path, float]]:
        """Rank files based on query relevance and dependency centrality. Return top_n."""
        if not files:
            return []

        from collections import defaultdict
        centrality: dict[str, float] = defaultdict(float)
        for dep in dependencies:
            src = dep.get("source", "")
            tgt = dep.get("target", "")
            if src:
                centrality[src] += 1
            if tgt:
                centrality[tgt] += 1
        max_cent = max(centrality.values()) if centrality else 1

        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        combined_scores: list[tuple[Path, float]] = []

        for path in files:
            rel_path = str(path.relative_to(self.root))
            cent_score = (centrality.get(rel_path, 0) / max_cent) if max_cent > 0 else 0

            if not query_terms:
                try:
                    stat = path.stat()
                    size_factor = min(stat.st_size / 100_000, 1.0)
                except OSError:
                    size_factor = 0.5
                score = (cent_score * 0.7) + (size_factor * 0.3)
            else:
                lexical_score = 0.0
                try:
                    content_str = path.read_text(encoding="utf-8", errors="replace").lower()
                    tokens_raw = re.findall(r"\b\w+\b", content_str)
                    tokens = [t for t in tokens_raw if len(t) > 2]
                except Exception:
                    tokens = []

                if tokens:
                    term_counts = Counter(tokens)
                    doc_len = len(tokens)
                    for term in query_terms:
                        if term in term_counts:
                            tf = term_counts[term] / doc_len
                            lexical_score += tf

                score = (lexical_score * 0.8) + (cent_score * 0.2)

            combined_scores.append((path, score))

        combined_scores.sort(key=lambda x: x[1], reverse=True)
        return combined_scores[:top_n]
