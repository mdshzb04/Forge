"""Forge Output Optimization Layer.

Optimizes command-line execution, build, test, and lint outputs before they
become context for the AI model, preserving critical diagnostics and failures.
"""

from __future__ import annotations

import re


class OutputOptimizer:
    """Optimizes verbose terminal, test, and build outputs."""

    def __init__(self, intensity: str = "off") -> None:
        self.intensity = intensity.lower()

    def optimize(self, text: str) -> str:
        """Compress output text based on the configured intensity level."""
        if not text or self.intensity == "off":
            return text

        lines = text.splitlines()
        if not lines:
            return text

        if self.intensity == "lite":
            return self._optimize_lite(lines)
        elif self.intensity == "full":
            return self._optimize_full(lines)
        elif self.intensity == "ultra":
            return self._optimize_ultra(lines)

        return text

    def _optimize_lite(self, lines: list[str]) -> str:
        """Lite: Remove consecutive empty lines, collapse consecutive duplicate lines, and compress progress bars."""
        result: list[str] = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].rstrip()
            if not line:
                # Collapse consecutive empty lines into a single one
                if not result or result[-1]:
                    result.append("")
                i += 1
                continue

            # Check for consecutive duplicate lines
            dup_count = 1
            while i + dup_count < n and lines[i + dup_count].rstrip() == line:
                dup_count += 1

            if dup_count > 1:
                result.append(f"{line} [repeated {dup_count} times]")
                i += dup_count
                continue

            # Compress consecutive progress updates
            if self._is_progress_line(line):
                # Consume consecutive progress lines and keep only the first & last
                progress_lines = [line]
                i += 1
                while i < n and self._is_progress_line(lines[i]):
                    progress_lines.append(lines[i].rstrip())
                    i += 1
                if len(progress_lines) > 2:
                    result.append(progress_lines[0])
                    result.append(f"  [... collapsed {len(progress_lines) - 2} progress updates ...]")
                    result.append(progress_lines[-1])
                else:
                    result.extend(progress_lines)
                continue

            result.append(line)
            i += 1

        return "\n".join(result)

    def _optimize_full(self, lines: list[str]) -> str:
        """Full: Group identical warnings, compress successful test results, and collapse duplicates."""
        # Run lite optimization first to clean up duplicate lines & progress lines
        lite_text = self._optimize_lite(lines)
        lite_lines = lite_text.splitlines()

        result: list[str] = []
        warnings_map: dict[str, int] = {}
        successful_tests: list[str] = []

        i = 0
        n = len(lite_lines)
        while i < n:
            line = lite_lines[i]

            # Group identical warnings
            if self._is_warning_line(line):
                # Clean trace info from warning to group them better
                norm_warning = re.sub(r'\d+', 'N', line)
                warnings_map[norm_warning] = warnings_map.get(norm_warning, 0) + 1
                i += 1
                continue

            # If warning sequence ended, output grouped warnings
            if warnings_map:
                for warn, count in warnings_map.items():
                    suffix = f" [repeated {count} times]" if count > 1 else ""
                    result.append(f"{warn}{suffix}")
                warnings_map.clear()

            # Compress long successful test lines (e.g. pytest PASSED outputs)
            if self._is_successful_test_line(line):
                successful_tests.append(line)
                i += 1
                continue

            if successful_tests:
                if len(successful_tests) > 1:
                    result.append(f"  [... {len(successful_tests)} successful tests collapsed ...]")
                    result.append(successful_tests[-1])
                else:
                    result.extend(successful_tests)
                successful_tests.clear()

            result.append(line)
            i += 1

        # Flush any remaining items
        if warnings_map:
            for warn, count in warnings_map.items():
                suffix = f" [repeated {count} times]" if count > 1 else ""
                result.append(f"{warn}{suffix}")
        if successful_tests:
            if len(successful_tests) > 1:
                result.append(f"  [... {len(successful_tests)} successful tests collapsed ...]")
                result.append(successful_tests[-1])
            else:
                result.extend(successful_tests)

        return "\n".join(result)

    def _optimize_ultra(self, lines: list[str]) -> str:
        """Ultra: Aggressively collapse success output, leaving only errors, stack traces, and diagnostics."""
        # Find if there are any failures or errors in the output
        has_failures = any(self._is_error_line(line) for line in lines)

        if not has_failures:
            # Entire command succeeded, collapse aggressively
            total_lines = len(lines)
            if total_lines > 5:
                # Return a summary showing success and count of collapsed lines
                return f"[Success] Command executed successfully. Collapsed {total_lines} lines of output."
            return "\n".join(lines)

        # If there are failures, keep error lines, warning lines, and stack trace contexts,
        # but collapse non-error blocks.
        result: list[str] = []
        n = len(lines)
        in_error_block = False
        collapsed_block_count = 0

        i = 0
        while i < n:
            line = lines[i]
            is_err = self._is_error_line(line)
            is_warn = self._is_warning_line(line)

            # Stack traces and pytest errors have surrounding context lines (like indentation or lines starting with '>')
            is_context = False
            if (
                not is_err
                and not is_warn
                and in_error_block
                and (line.startswith((" ", "\t", ">", "E ")) or len(line.strip()) < 5)
            ):
                is_context = True

            if is_err or is_warn or is_context:
                if collapsed_block_count > 0:
                    result.append(f"  [... collapsed {collapsed_block_count} successful/log lines ...]")
                    collapsed_block_count = 0
                result.append(line)
                in_error_block = True
            else:
                collapsed_block_count += 1
                in_error_block = False

            i += 1

        if collapsed_block_count > 0:
            result.append(f"  [... collapsed {collapsed_block_count} successful/log lines ...]")

        return "\n".join(result)

    def _is_progress_line(self, line: str) -> bool:
        """Return True if the line contains progress updates (percentages, progress bars)."""
        line_lower = line.lower()
        if "/" in line and any(unit in line_lower for unit in ["kb/s", "mb/s", "bytes/s", "b/s"]):
            return True
        if re.search(r'\[?\s*\d+%\s*\]?', line):
            return True
        return (
            "[" in line
            and "]" in line
            and ("#" in line or "=" in line or "-" in line)
            and len(re.findall(r'[#=\-]', line)) > 5
        )

    def _is_warning_line(self, line: str) -> bool:
        """Return True if the line is a compiler/linter warning."""
        line_lower = line.lower()
        if any(p in line_lower for p in ["warning:", "[warning]", "[warn]"]):
            return True
        return bool(re.search(r'\b\w+\.\w+:\d+(:\d+)?:?\s*warning:', line_lower))

    def _is_error_line(self, line: str) -> bool:
        """Return True if the line contains a compiler error, failed assertion, or exception trace."""
        line_lower = line.lower()
        if "traceback (most recent call last)" in line_lower:
            return True
        if re.search(r'file ".*", line \d+', line_lower):
            return True
        if any(err in line for err in ["AssertionError", "ValueError", "TypeError", "KeyError", "NameError", "AttributeError", "IndexError", "FileNotFoundError", "RuntimeError"]):
            return True
        if (
            any(
                p in line_lower
                for p in ["error:", "failed:", "[error]", "[fail]", "critical:", "fatal:"]
            )
            and not re.search(r'\b0\s+failed\b', line_lower)
            and not re.search(r'\bno\s+errors\b', line_lower)
        ):
            return True
        if line.startswith(("E   ", ">   ")):
            return True
        if line_lower.startswith(("fail: ", "error: ")):
            return True
        return bool(re.search(r'\b\w+\.\w+:\d+(:\d+)?:?\s*error:', line_lower))

    def _is_successful_test_line(self, line: str) -> bool:
        """Return True if the line indicates a successfully passed test case."""
        return "PASSED" in line or (line.strip() == "." and len(line) < 3)
