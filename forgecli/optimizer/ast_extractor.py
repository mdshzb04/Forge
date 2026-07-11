"""AST Extractor and Codebase Pruner.

Uses Python's native 'ast' parser and robust regex-based structural parsers
for other languages to extract classes, functions, structs, interfaces, methods,
and imports. Supports deep pruning of source files to retain only selected nodes.
"""



from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass

class ASTNode:

    name: str

    kind: str

    start_line: int

    end_line: int

    content: str

    dependencies: list[str] = field(default_factory=list)





class ASTExtractor:

    """Extracts structural AST nodes from source files and prunes unused constructs."""



    @staticmethod

    def extract_nodes(path: Path) -> list[ASTNode]:

        """Extract all structural nodes (classes, functions, etc.) from the file."""

        if not path.exists() or not path.is_file():

            return []



        suffix = path.suffix.lower()

        content = path.read_text(encoding="utf-8", errors="replace")



        if suffix == ".py":

            return ASTExtractor._extract_python(content)

        elif suffix in (".js", ".ts", ".jsx", ".tsx"):

            return ASTExtractor._extract_js_ts(content)

        elif suffix == ".rs":

            return ASTExtractor._extract_rust(content)

        elif suffix == ".go":

            return ASTExtractor._extract_go(content)

        else:

            return []



    @staticmethod

    def prune_file(path: Path, keep_names: set[str]) -> str:

        """Return file contents containing only the imports and the nodes in keep_names."""

        nodes = ASTExtractor.extract_nodes(path)

        if not nodes:

            return path.read_text(encoding="utf-8", errors="replace")



        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        keep_lines = [False] * len(lines)





        for node in nodes:

            if node.kind == "import":

                for idx in range(node.start_line - 1, node.end_line):

                    if idx < len(keep_lines):

                        keep_lines[idx] = True





        for node in nodes:

            if node.name in keep_names or any(node.name.startswith(name + ".") for name in keep_names):

                for idx in range(node.start_line - 1, node.end_line):

                    if idx < len(keep_lines):

                        keep_lines[idx] = True





        pruned_lines = []

        in_omitted_block = False



        for idx, line in enumerate(lines):

            if keep_lines[idx]:

                if in_omitted_block:

                    pruned_lines.append("# ... [code collapsed to save tokens] ...")

                    in_omitted_block = False

                pruned_lines.append(line)

            else:

                if not in_omitted_block:

                    in_omitted_block = True



        if in_omitted_block:

            pruned_lines.append("# ... [code collapsed to save tokens] ...")



        return "\n".join(pruned_lines)



    @staticmethod

    def _extract_python(content: str) -> list[ASTNode]:

        """Extract nodes using Python's native AST parser."""

        nodes: list[ASTNode] = []

        try:

            tree = ast.parse(content)

            lines = content.splitlines()



            for node in ast.walk(tree):

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):

                    start = getattr(node, "lineno", 1)

                    end = getattr(node, "end_lineno", start)

                    node_content = "\n".join(lines[start - 1 : end])

                    kind = "class" if isinstance(node, ast.ClassDef) else "function"





                    deps = []

                    for child in ast.walk(node):

                        if isinstance(child, ast.Name):

                            deps.append(child.id)

                        elif isinstance(child, ast.Attribute):

                            deps.append(child.attr)



                    nodes.append(

                        ASTNode(

                            name=node.name,

                            kind=kind,

                            start_line=start,

                            end_line=end,

                            content=node_content,

                            dependencies=list(set(deps)),

                        )

                    )

                elif isinstance(node, (ast.Import, ast.ImportFrom)):

                    start = getattr(node, "lineno", 1)

                    end = getattr(node, "end_lineno", start)

                    node_content = "\n".join(lines[start - 1 : end])

                    nodes.append(

                        ASTNode(

                            name="import",

                            kind="import",

                            start_line=start,

                            end_line=end,

                            content=node_content,

                        )

                    )

        except Exception:



            pass

        return nodes



    @staticmethod

    def _extract_js_ts(content: str) -> list[ASTNode]:

        """Extract classes, functions, and interfaces using robust regex scanners."""

        nodes: list[ASTNode] = []

        lines = content.splitlines()





        patterns = [

            (r"^(?:export\s+)?class\s+([A-Za-z0-9_]+)", "class"),

            (r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)", "function"),

            (r"^(?:export\s+)?interface\s+([A-Za-z0-9_]+)", "interface"),

            (r"^(?:export\s+)?enum\s+([A-Za-z0-9_]+)", "enum"),

            (r"^(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>", "function"),

        ]





        for pattern, kind in patterns:

            for match in re.finditer(pattern, content, re.MULTILINE):

                name = match.group(1)

                start_char = match.start()

                start_line = content[:start_char].count("\n") + 1





                open_braces = 0

                end_line = start_line

                found_start = False



                for idx in range(start_char, len(content)):

                    char = content[idx]

                    if char == "{":

                        open_braces += 1

                        found_start = True

                    elif char == "}":

                        open_braces -= 1

                    if found_start and open_braces == 0:

                        end_line = content[:idx].count("\n") + 1

                        break

                else:



                    end_line = min(start_line + 20, len(lines))



                node_content = "\n".join(lines[start_line - 1 : end_line])

                nodes.append(

                    ASTNode(

                        name=name,

                        kind=kind,

                        start_line=start_line,

                        end_line=end_line,

                        content=node_content,

                    )

                )





        import_re = re.compile(

            r"^\s*(?:import\s+.*?\s+from\s+['\"][^'\"]+['\"]|import\s+['\"][^'\"]+['\"]|const\s+.*?\s*=\s*require\(.*?\))",

            re.MULTILINE,

        )

        for match in import_re.finditer(content):

            start_line = content[: match.start()].count("\n") + 1

            end_line = content[: match.end()].count("\n") + 1

            node_content = content[match.start() : match.end()]

            nodes.append(

                ASTNode(

                    name="import",

                    kind="import",

                    start_line=start_line,

                    end_line=end_line,

                    content=node_content,

                )

            )



        return nodes



    @staticmethod

    def _extract_rust(content: str) -> list[ASTNode]:

        """Extract structs, enums, impl blocks, and traits from Rust code."""

        nodes: list[ASTNode] = []

        lines = content.splitlines()



        patterns = [

            (r"^(?:pub\s+)?struct\s+([A-Za-z0-9_]+)", "struct"),

            (r"^(?:pub\s+)?enum\s+([A-Za-z0-9_]+)", "enum"),

            (r"^(?:pub\s+)?trait\s+([A-Za-z0-9_]+)", "trait"),

            (r"^(?:pub\s+)?fn\s+([A-Za-z0-9_]+)", "function"),

            (r"^impl(?:\s+<.*?>)?\s+([A-Za-z0-9_]+)", "class"),

        ]



        for pattern, kind in patterns:

            for match in re.finditer(pattern, content, re.MULTILINE):

                name = match.group(1)

                start_char = match.start()

                start_line = content[:start_char].count("\n") + 1



                open_braces = 0

                end_line = start_line

                found_start = False



                for idx in range(start_char, len(content)):

                    char = content[idx]

                    if char == "{":

                        open_braces += 1

                        found_start = True

                    elif char == "}":

                        open_braces -= 1

                    if found_start and open_braces == 0:

                        end_line = content[:idx].count("\n") + 1

                        break

                else:

                    end_line = min(start_line + 30, len(lines))



                node_content = "\n".join(lines[start_line - 1 : end_line])

                nodes.append(

                    ASTNode(

                        name=name,

                        kind=kind,

                        start_line=start_line,

                        end_line=end_line,

                        content=node_content,

                    )

                )





        use_re = re.compile(r"^\s*(?:pub\s+)?use\s+[^;]+;", re.MULTILINE)

        for match in use_re.finditer(content):

            start_line = content[: match.start()].count("\n") + 1

            end_line = content[: match.end()].count("\n") + 1

            node_content = content[match.start() : match.end()]

            nodes.append(

                ASTNode(

                    name="import",

                    kind="import",

                    start_line=start_line,

                    end_line=end_line,

                    content=node_content,

                )

            )



        return nodes



    @staticmethod

    def _extract_go(content: str) -> list[ASTNode]:

        """Extract structs, interfaces, and functions from Go code."""

        nodes: list[ASTNode] = []

        lines = content.splitlines()



        patterns = [

            (r"^type\s+([A-Za-z0-9_]+)\s+struct", "struct"),

            (r"^type\s+([A-Za-z0-9_]+)\s+interface", "interface"),

            (r"^func\s+([A-Za-z0-9_]+)\(", "function"),

            (r"^func\s+\([^)]+\)\s+([A-Za-z0-9_]+)\(", "method"),

        ]



        for pattern, kind in patterns:

            for match in re.finditer(pattern, content, re.MULTILINE):

                name = match.group(1)

                start_char = match.start()

                start_line = content[:start_char].count("\n") + 1



                open_braces = 0

                end_line = start_line

                found_start = False



                for idx in range(start_char, len(content)):

                    char = content[idx]

                    if char == "{":

                        open_braces += 1

                        found_start = True

                    elif char == "}":

                        open_braces -= 1

                    if found_start and open_braces == 0:

                        end_line = content[:idx].count("\n") + 1

                        break

                else:

                    end_line = min(start_line + 20, len(lines))



                node_content = "\n".join(lines[start_line - 1 : end_line])

                nodes.append(

                    ASTNode(

                        name=name,

                        kind=kind,

                        start_line=start_line,

                        end_line=end_line,

                        content=node_content,

                    )

                )





        import_re = re.compile(r"^\s*import\s+\([^)]+\)", re.MULTILINE | re.DOTALL)

        for match in import_re.finditer(content):

            start_line = content[: match.start()].count("\n") + 1

            end_line = content[: match.end()].count("\n") + 1

            node_content = content[match.start() : match.end()]

            nodes.append(

                ASTNode(

                    name="import",

                    kind="import",

                    start_line=start_line,

                    end_line=end_line,

                    content=node_content,

                )

            )



        single_import_re = re.compile(r"^\s*import\s+['\"][^'\"]+['\"]", re.MULTILINE)

        for match in single_import_re.finditer(content):

            start_line = content[: match.start()].count("\n") + 1

            end_line = content[: match.end()].count("\n") + 1

            node_content = content[match.start() : match.end()]

            nodes.append(

                ASTNode(

                    name="import",

                    kind="import",

                    start_line=start_line,

                    end_line=end_line,

                    content=node_content,

                )

            )



        return nodes

