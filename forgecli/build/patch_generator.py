"""Patch Generation and Recovery Layer.

Ensures LLM response contains a valid unified diff that applies with git apply.
If the LLM falls back to outputting full files or markdown code blocks, this
layer dynamically computes a minimal unified diff against the original source file.
"""

from __future__ import annotations

import difflib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class PatchGenerator:
    """Post-processes LLM responses to generate or validate unified diff patches."""

    @staticmethod
    def ensure_patch(content: str, root: Path, prompt: str) -> str:
        """Ensure the content is a valid unified diff.

        If not, attempts to parse and compute a diff against the target file.
        """
        stripped = content.strip()

        # 1. Check if it's already a unified diff
        if (
            "diff --git" in stripped
            or ("--- " in stripped and "+++ " in stripped)
            or (stripped.startswith("@@ ") and "---" in stripped)
        ):
            return content

        # 2. Extract content from code block if enclosed in fences
        code_block = PatchGenerator.extract_code_block(stripped)
        if not code_block:
            code_block = stripped

        # 3. Find the target file we are trying to edit
        target_file = PatchGenerator.find_target_file(prompt, code_block, root)
        if not target_file or not target_file.is_file():
            return content

        # 4. Generate a minimal unified diff between the original file and the new code block
        try:
            original_content = target_file.read_text(encoding="utf-8", errors="replace")
            # If the output is already identical, no-op
            if original_content.strip() == code_block.strip():
                return content

            rel_path = str(target_file.relative_to(root))
            
            diff_lines = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                code_block.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
            generated_diff = "".join(diff_lines)
            if generated_diff:
                logger.info(f"Successfully recovered full-file fallback as unified diff for {rel_path}")
                return generated_diff
        except Exception as e:
            logger.debug(f"Failed to generate diff: {e}")

        return content

    @staticmethod
    def extract_code_block(text: str) -> str | None:
        """Extract the content of the first markdown code block, if any."""
        match = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def find_target_file(prompt: str, code: str, root: Path) -> Path | None:
        """Find the file being edited based on prompt names or content characteristics."""
        # Search for file names mentioned in prompt or first few lines of code
        potential_names = re.findall(r"\b[\w\-./]+\.\w+\b", prompt + "\n" + code[:200])
        
        # Deduplicate while preserving order
        seen = set()
        candidates = []
        for name in potential_names:
            name_clean = name.lstrip("./")
            if name_clean not in seen:
                seen.add(name_clean)
                candidates.append(name_clean)

        for candidate in candidates:
            path = root / candidate
            if path.is_file():
                return path

        # Fallback: scan root files for a filename match if only a base name was extracted
        for candidate in candidates:
            base_name = Path(candidate).name
            for file_path in root.rglob("*"):
                if file_path.is_file() and file_path.name == base_name:
                    # Ignore skip dirs
                    skip_dirs = {".git", ".venv", "node_modules", "dist", "build", ".forge"}
                    if not any(part in skip_dirs for part in file_path.parts):
                        return file_path

        return None
