"""Context Compression Engine.

Prunes redundant characters, collapses whitespaces, strips markdown templates,
and minimizes structured data (JSON, YAML, XML) without losing semantic meaning.
"""



from __future__ import annotations

import json
import re
from typing import Any


class ContextCompressionEngine:

    """Compresses arbitrary text context and structured formats to minimize tokens."""



    @staticmethod

    def collapse_whitespace(text: str) -> str:

        """Replace multiple spaces with a single space, and consecutive newlines with a single newline."""

        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]

        rejoined = "\n".join(lines)

        return re.sub(r"\n+", "\n", rejoined).strip()



    @staticmethod

    def remove_boilerplate(text: str) -> str:

        """Strip markdown comment blocks, system banners, and divider templates."""



        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)



        text = re.sub(r"^[=\-_#\*]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text



    @staticmethod

    def deduplicate_paragraphs(text: str, min_length: int = 40) -> str:

        """Detect duplicate paragraphs or long sentences and replace subsequent occurrences with references."""

        paragraphs = text.split("\n\n")

        seen: dict[str, str] = {}

        result: list[str] = []

        ref_counter = 1



        for p in paragraphs:

            trimmed = p.strip()

            if len(trimmed) >= min_length:



                norm = re.sub(r"\s+", " ", trimmed).lower()

                if norm in seen:

                    result.append(f"[REF: {seen[norm]}]")

                    continue

                else:

                    ref_id = f"R{ref_counter}"

                    seen[norm] = ref_id

                    ref_counter += 1



                    result.append(f"[{ref_id}] {trimmed}")

            else:

                result.append(p)



        return "\n\n".join(result)



    @staticmethod

    def compress_json(raw_json: str) -> str:

        """Parse JSON and serialize it compactly, omitting nulls, empty collections, and unnecessary whitespaces."""

        try:

            data = json.loads(raw_json)

            minimized = ContextCompressionEngine._minimize_object(data)

            if minimized is None or minimized == {} or minimized == []:

                return ""

            return json.dumps(minimized, separators=(",", ":"))

        except Exception:

            return raw_json



    @staticmethod

    def compress_yaml(raw_yaml: str) -> str:

        """Minimize YAML text by parsing it, stripping empty keys, and generating a compact YAML representation."""

        try:

            import yaml

            data = yaml.safe_load(raw_yaml)

            minimized = ContextCompressionEngine._minimize_object(data)

            if minimized is None or minimized == {} or minimized == []:

                return ""



            return yaml.safe_dump(minimized, default_flow_style=True, sort_keys=False).strip()

        except Exception:

            return raw_yaml



    @staticmethod

    def compress_xml(raw_xml: str) -> str:

        """Strip comments, whitespaces, and empty elements from raw XML code."""





        xml = re.sub(r"<!--.*?-->", "", raw_xml, flags=re.DOTALL)



        xml = re.sub(r">\s+<", "><", xml)



        xml = re.sub(r'\s+\w+=""', "", xml)

        return xml.strip()



    @staticmethod

    def _minimize_object(obj: Any) -> Any:

        """Recursively prune empty fields, empty objects, empty arrays, and null values from objects."""

        if isinstance(obj, dict):

            new_dict = {}

            for k, v in obj.items():

                min_v = ContextCompressionEngine._minimize_object(v)

                if min_v not in (None, "", {}, []):

                    new_dict[k] = min_v

            return new_dict

        elif isinstance(obj, list):

            new_list = []

            for item in obj:

                min_item = ContextCompressionEngine._minimize_object(item)

                if min_item not in (None, "", {}, []):

                    new_list.append(min_item)

            return new_list

        return obj



    @staticmethod

    def remove_duplicate_imports(text: str) -> str:

        """Strip duplicate import statements within file boundaries to save tokens."""

        lines = text.splitlines()

        seen_imports = set()

        result = []

        for line in lines:

            stripped = line.strip()

            is_import = (

                stripped.startswith("import ") or

                (stripped.startswith("from ") and " import " in stripped) or

                ((stripped.startswith("const ") or stripped.startswith("let ") or stripped.startswith("import ")) and "require(" in stripped)

            )

            if is_import:

                normalized = re.sub(r"\s+", " ", stripped)

                if normalized in seen_imports:

                    continue

                seen_imports.add(normalized)

            result.append(line)

        return "\n".join(result)



    @staticmethod

    def remove_repeated_diagnostics(text: str) -> str:

        """Collapse repeated stack traces, error diagnostics, and warning messages."""

        lines = text.splitlines()

        result = []

        last_line = None

        repeat_count = 0



        for line in lines:

            stripped = line.strip()

            is_diagnostic = any(x in stripped.lower() for x in ["error", "warning", "traceback", "exception", "failed", "at "])

            if is_diagnostic and stripped == last_line:

                repeat_count += 1

                continue

            else:

                if repeat_count > 0:

                    result.append(f"... [Repeated {repeat_count} times] ...")

                    repeat_count = 0

                result.append(line)

                last_line = stripped if is_diagnostic else None



        if repeat_count > 0:

            result.append(f"... [Repeated {repeat_count} times] ...")



        return "\n".join(result)



    @staticmethod
    def remove_duplicate_markdown_blocks(text: str) -> str:
        """Find duplicate code blocks and replace subsequent ones with a concise reference."""
        import hashlib
        pattern = re.compile(r"```(?:\w+)?\n.*?\n```", re.DOTALL)

        seen_hashes = {}
        last_idx = 0
        parts = []

        for match in pattern.finditer(text):
            parts.append(text[last_idx:match.start()])
            block_text = match.group(0)

            lines = block_text.splitlines()
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
            h = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

            if h in seen_hashes:
                ref = seen_hashes[h]
                parts.append(f"```\n[Duplicate code block: see {ref}]\n```")
            else:
                ref_name = f"Code block {len(seen_hashes) + 1}"
                seen_hashes[h] = ref_name
                parts.append(block_text)

            last_idx = match.end()

        parts.append(text[last_idx:])
        return "".join(parts)



    def compress_all(self, text: str) -> str:

        """Run all compression routines sequentially."""

        text = self.remove_boilerplate(text)

        text = self.remove_duplicate_markdown_blocks(text)

        text = self.remove_duplicate_imports(text)

        text = self.remove_repeated_diagnostics(text)

        text = self.deduplicate_paragraphs(text)

        text = self.collapse_whitespace(text)

        return text
