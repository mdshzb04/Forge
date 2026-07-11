"""Quality Validation Engine.

Ensures syntax correctness of compressed code files and validates that no
critical dependencies or symbols are lost during context pruning.
"""



from __future__ import annotations

import ast


class QualityValidator:

    """Verifies syntactic and semantic integrity of optimized context segments."""



    @staticmethod

    def validate_python_syntax(code: str) -> bool:

        """Return True if the Python code block parses cleanly without syntax errors."""

        try:

            ast.parse(code)

            return True

        except SyntaxError:

            return False



    @staticmethod

    def validate_braces_balance(code: str) -> bool:

        """Validate that braces/parentheses match, indicating correct blocks were kept in JS/TS/Go/Rust."""

        stack = []

        mapping = {")": "(", "}": "{", "]": "["}





        code_clean = re.sub(r"//.*|/\*.*?\*/", "", code)

        code_clean = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "", code_clean)



        for char in code_clean:

            if char in mapping.values():

                stack.append(char)

            elif char in mapping:

                if not stack or stack[-1] != mapping[char]:

                    return False

                stack.pop()

        return len(stack) == 0



    @staticmethod

    def verify_dependency_integrity(

        pruned_files: dict[str, str],

        dependencies: list[dict[str, str]],

    ) -> list[str]:

        """Check if any pruned file imports a local file/module that was omitted.

        Returns a list of warning messages detailing missing references.
        """

        warnings = []

        for dep in dependencies:

            src = dep.get("source")

            tgt = dep.get("target")

            if src in pruned_files and tgt not in pruned_files:



                if not tgt.startswith((".", "/")) and "/" not in tgt:

                    continue

                warnings.append(

                    f"Warning: '{src}' imports '{tgt}' which was omitted from the optimized context."

                )

        return warnings





import re

