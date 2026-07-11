"""Intelligent Retrieval Engine.

Minimizes context windows by dynamically resolving code dependencies (import chains)
and terminating retrieval early when semantic coverage matches the user's request.
"""



from __future__ import annotations

from pathlib import Path


class IntelligentRetrievalManager:

    """Dynamically resolves required symbols and import dependencies while containing token growth."""



    def __init__(

        self,

        repo_root: Path,

        dependencies: list[dict[str, str]],

        symbols: list[dict[str, Any]],

        cache: Any = None,

        fingerprint: str = "",

    ) -> None:

        self.root = Path(repo_root).resolve()

        self.dependencies = dependencies

        self.symbols = symbols

        self.cache = cache

        self.fingerprint = fingerprint





        self.symbol_to_file = {}

        for s in symbols:

            name = s.get("name")

            f = s.get("file")

            if name and f:

                self.symbol_to_file[name.lower()] = f





        self.imports = {}

        self.imported_by = {}

        for dep in dependencies:

            src = dep.get("source")

            tgt = dep.get("target")

            if src and tgt:

                self.imports.setdefault(src, []).append(tgt)

                self.imported_by.setdefault(tgt, []).append(src)



    def retrieve_context_for_query(

        self,

        query: str,

        max_depth: int = 2,

    ) -> dict[str, set[str]]:

        """Identify only the files and specific symbols needed to answer the query.

        Returns a mapping of relative file path -> set of symbol names to retain.
        """
        # Graph traversals and semantic search cache
        cache_key = f"graph_traverse:{query}:{max_depth}"
        if self.cache and self.fingerprint:
            cached = self.cache.get("graph_traversal", cache_key, self.fingerprint)
            if cached is not None:
                return {k: set(v) for k, v in cached.items()}

        needed_symbols = self._extract_query_symbols(query)

        retrieved: dict[str, set[str]] = {}





        files_to_scan = set()

        for sym in needed_symbols:

            norm_sym = sym.lower()

            if norm_sym in self.symbol_to_file:

                filepath = self.symbol_to_file[norm_sym]

                files_to_scan.add(filepath)

                retrieved.setdefault(filepath, set()).add(sym)





        visited = set(files_to_scan)

        queue = [(f, 0) for f in files_to_scan]



        while queue:

            current_file, depth = queue.pop(0)

            if depth >= max_depth:

                continue





            imported = self.imports.get(current_file, [])

            for imp in imported:



                resolved = self._resolve_import_to_file(current_file, imp)

                if resolved and resolved not in visited:

                    visited.add(resolved)

                    queue.append((resolved, depth + 1))



                    retrieved.setdefault(resolved, set())

        if self.cache and self.fingerprint:
            serialized = {k: list(v) for k, v in retrieved.items()}
            self.cache.set("graph_traversal", cache_key, serialized, self.fingerprint)

        return retrieved



    def _extract_query_symbols(self, query: str) -> set[str]:

        """Find potential class, function, or structural name tokens mentioned in the query."""

        cache_key = f"sym_lookup:{query}"
        if self.cache and self.fingerprint:
            cached = self.cache.get("symbol_lookup", cache_key, self.fingerprint)
            if cached is not None:
                return set(cached)

        tokens = set(re.findall(r"\b[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*\b", query))



        known_lower = {s.get("name", "").lower(): s.get("name") for s in self.symbols}

        matched = set()

        for tok in tokens:



            subtokens = tok.split(".")

            for sub in subtokens:

                sub_lower = sub.lower()

                if sub_lower in known_lower:

                    matched.add(known_lower[sub_lower])

        if self.cache and self.fingerprint:
            self.cache.set("symbol_lookup", cache_key, list(matched), self.fingerprint)

        return matched



    def _resolve_import_to_file(self, source_file: str, import_target: str) -> str | None:

        """Translate import statements (like from x import y or import z) into relative repository files."""

        cache_key = f"dep_resolve:{source_file}:{import_target}"
        if self.cache and self.fingerprint:
            cached = self.cache.get("dependency_traversal", cache_key, self.fingerprint)
            if cached is not None:
                return cached or None

        source_path = Path(source_file)





        resolved = None

        candidate_rel = source_path.parent / import_target

        for ext in (".py", ".ts", ".js", ".go", ".rs"):

            test_path = candidate_rel.with_suffix(ext)

            if (self.root / test_path).exists():

                resolved = str(test_path)
                break

        if not resolved:

            normalized_tgt = import_target.replace(".", "/")

            for ext in (".py", ".ts", ".js", ".go", ".rs"):

                test_path = Path(normalized_tgt).with_suffix(ext)

                if (self.root / test_path).exists():

                    resolved = str(test_path)
                    break

            if not resolved:

                dir_path = Path(normalized_tgt)

                if (self.root / dir_path).is_dir():

                    for index_file in ("__init__.py", "index.ts", "index.js"):

                        test_index = dir_path / index_file

                        if (self.root / test_index).exists():

                            resolved = str(test_index)
                            break

        if self.cache and self.fingerprint:
            self.cache.set("dependency_traversal", cache_key, resolved or "", self.fingerprint)

        return resolved





import re
from typing import Any

