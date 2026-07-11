"""Language-aware comment and docstring stripping engine.

Supports Python, JS, TS, Go, Rust, Java, C, and C++. Operates on temporary context
copies to ensure source code files are never modified. Handles license headers,
compiler directives, and configuration levels: off, lite, full, ultra.
"""

from __future__ import annotations

import io
import re
import tokenize


class CommentStripper:
    """Strips comments and docstrings from source code according to the configured mode."""

    LICENSE_KEYWORDS = {
        "copyright", "license", "author", "created by", "credits",
        "contributor", "apache", "mozilla", "bsd", "mit license", "gpl"
    }

    COMPILER_DIRECTIVES = {
        "go:", "export", "lint:", "sys", "eslint-disable", "eslint-enable",
        "eslint", "@ts-nocheck", "@ts-check", "@ts-ignore", "pragma",
        "include", "define", "ifdef", "ifndef", "endif", "clang", "gcc",
        "msvc", "unused"
    }

    @classmethod
    def is_license_header(cls, text: str, pos_in_file: int) -> bool:
        """Return True if the text resembles a license header near the top of the file."""
        if pos_in_file > 3000:  # Must be near the top
            return False
        lower_text = text.lower()
        return any(kw in lower_text for kw in cls.LICENSE_KEYWORDS)

    @classmethod
    def is_compiler_directive(cls, text: str) -> bool:
        """Return True if the text represents a compiler directive or linter hint."""
        # Strip comment characters and whitespace
        clean = text.strip().lstrip("/#* \t")
        # Match directives at start
        for directive in cls.COMPILER_DIRECTIVES:
            if clean.startswith(directive) or clean.lower().startswith(directive):
                return True
        # Check standard directive patterns
        if re.match(r"^[A-Za-z0-9_]+:", clean):  # E.g. go:generate
            return True
        return False

    @classmethod
    def strip_comments(cls, content: str, filepath: str | None = None, mode: str = "off") -> str:
        """Strip comments and docstrings based on the file extension and mode."""
        if mode == "off":
            return content

        suffix = ""
        if filepath:
            suffix = filepath.split(".")[-1].lower() if "." in filepath else ""

        if suffix == "py":
            return cls._strip_python(content, mode)
        elif suffix in ("js", "ts", "jsx", "tsx", "go", "rs", "java", "c", "cpp", "cc", "h", "hpp"):
            return cls._strip_c_style(content, mode)
        else:
            # Fallback for unrecognized extension: try C-style first, then fallback
            return cls._strip_c_style(content, mode)

    @classmethod
    def _strip_python(cls, content: str, mode: str) -> str:
        """Python tokenize-based comment and docstring stripper."""
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
        except Exception:
            # Fallback to lines parse if tokenization fails (e.g. syntax error in middle of build)
            return content

        # Identify docstrings: a STRING token that is the first statement of a logical line,
        # followed by a NEWLINE or NL.
        docstring_tokens = set()
        
        # Track logical line start and preceding tokens
        logical_line_start = True
        preceding_non_space = None
        current_logical_tokens = []

        for idx, tok in enumerate(tokens):
            if tok.type in (tokenize.NL, tokenize.NEWLINE):
                # End of logical line, check if the single expression was a string
                non_space_toks = [t for t in current_logical_tokens if t.type not in (tokenize.INDENT, tokenize.DEDENT)]
                if len(non_space_toks) == 1 and non_space_toks[0].type == tokenize.STRING:
                    docstring_tokens.add(non_space_toks[0])
                elif len(non_space_toks) > 1 and non_space_toks[0].type == tokenize.STRING:
                    # Could be string followed by comment
                    first = non_space_toks[0]
                    rest = non_space_toks[1:]
                    if all(t.type == tokenize.COMMENT for t in rest):
                        docstring_tokens.add(first)
                
                logical_line_start = True
                current_logical_tokens = []
            elif tok.type == tokenize.INDENT:
                logical_line_start = True
            elif tok.type == tokenize.DEDENT:
                pass
            else:
                current_logical_tokens.append(tok)
                # Check for inline docstring on same line as def (e.g., def foo(): "docstring")
                if tok.type == tokenize.STRING and idx > 0:
                    prev = tokens[idx - 1]
                    # If preceding was colon and next is newline/NL/comment
                    if prev.string == ":" and idx + 1 < len(tokens) and tokens[idx + 1].type in (tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT):
                        docstring_tokens.add(tok)
                logical_line_start = False

        # Reconstruct content
        out = []
        last_line = 1
        last_col = 0

        for tok in tokens:
            # Handle source alignment and spacing
            if tok.start[0] > last_line:
                out.append("\n" * (tok.start[0] - last_line))
                last_col = 0
            if tok.start[1] > last_col and tok.start[0] == last_line:
                out.append(" " * (tok.start[1] - last_col))

            last_line = tok.end[0]
            last_col = tok.end[1]

            # Decide whether to emit token
            if tok.type == tokenize.COMMENT:
                comment_text = tok.string
                # Keep license or compiler directives
                if cls.is_license_header(comment_text, tok.start[0] * 50) or cls.is_compiler_directive(comment_text):
                    out.append(tok.string)
                elif mode == "lite":
                    # In lite mode, keep comments that are on their own line (only spaces/tabs before it)
                    line_prefix = tok.line[:tok.start[1]]
                    if not line_prefix.strip():
                        out.append(tok.string)
                    else:
                        # Replace with empty string (strips inline comment)
                        pass
                else:
                    # In full and ultra mode, strip the comment
                    pass
            elif tok in docstring_tokens:
                # Docstring token
                if mode == "lite":
                    out.append(tok.string)  # Keep docstring in lite
                else:
                    # Strip in full/ultra
                    pass
            else:
                out.append(tok.string)

        result = "".join(out)
        if mode == "ultra":
            result = cls._compress_whitespace(result)
        return result

    @classmethod
    def _strip_c_style(cls, content: str, mode: str) -> str:
        """State machine to strip C-style comments (// and /*) safely without breaking string literals."""
        out = []
        i = 0
        n = len(content)
        state = "DEFAULT"
        comment_start = 0

        while i < n:
            char = content[i]
            next_char = content[i + 1] if i + 1 < n else ""

            if state == "DEFAULT":
                if char == "/" and next_char == "/":
                    state = "SINGLE_LINE_COMMENT"
                    comment_start = i
                    i += 2
                elif char == "/" and next_char == "*":
                    state = "MULTI_LINE_COMMENT"
                    comment_start = i
                    i += 2
                elif char == '"':
                    state = "STRING_DOUBLE"
                    out.append(char)
                    i += 1
                elif char == "'":
                    state = "STRING_SINGLE"
                    out.append(char)
                    i += 1
                elif char == "`":
                    state = "STRING_BACKTICK"
                    out.append(char)
                    i += 1
                else:
                    out.append(char)
                    i += 1

            elif state == "SINGLE_LINE_COMMENT":
                if char == "\n":
                    # End comment, evaluate if we preserve it
                    comment_text = content[comment_start:i]
                    if cls.is_license_header(comment_text, comment_start) or cls.is_compiler_directive(comment_text):
                        out.append(comment_text)
                    elif mode == "lite":
                        # Preserve if it starts the line (i.e. only whitespace before it on the line)
                        line_prefix = "".join(out[-100:]).split("\n")[-1]
                        if not line_prefix.strip():
                            out.append(comment_text)
                    
                    out.append("\n")
                    state = "DEFAULT"
                    i += 1
                else:
                    i += 1

            elif state == "MULTI_LINE_COMMENT":
                if char == "*" and next_char == "/":
                    comment_text = content[comment_start:i + 2]
                    if cls.is_license_header(comment_text, comment_start) or cls.is_compiler_directive(comment_text):
                        out.append(comment_text)
                    elif mode == "lite":
                        # Lite mode keeps block comments
                        out.append(comment_text)
                    
                    state = "DEFAULT"
                    i += 2
                else:
                    i += 1

            elif state == "STRING_DOUBLE":
                if char == "\\" and next_char == '"':
                    out.append(char)
                    out.append(next_char)
                    i += 2
                elif char == '"':
                    out.append(char)
                    state = "DEFAULT"
                    i += 1
                else:
                    out.append(char)
                    i += 1

            elif state == "STRING_SINGLE":
                if char == "\\" and next_char == "'":
                    out.append(char)
                    out.append(next_char)
                    i += 2
                elif char == "'":
                    out.append(char)
                    state = "DEFAULT"
                    i += 1
                else:
                    out.append(char)
                    i += 1

            elif state == "STRING_BACKTICK":
                if char == "\\" and next_char == "`":
                    out.append(char)
                    out.append(next_char)
                    i += 2
                elif char == "`":
                    out.append(char)
                    state = "DEFAULT"
                    i += 1
                else:
                    out.append(char)
                    i += 1

        # Handle unfinished single line comment at EOF
        if state == "SINGLE_LINE_COMMENT":
            comment_text = content[comment_start:n]
            if cls.is_license_header(comment_text, comment_start) or cls.is_compiler_directive(comment_text):
                out.append(comment_text)

        result = "".join(out)
        if mode == "ultra":
            result = cls._compress_whitespace(result)
        return result

    @classmethod
    def _compress_whitespace(cls, text: str) -> str:
        """Aggressively removes empty lines, trailing whitespaces, and internal consecutive whitespaces."""
        lines = text.splitlines()
        compressed = []
        for line in lines:
            if not line.strip():
                continue
            # Preserve indentation at start of line
            match = re.match(r"^([ \t]*)", line)
            indent = match.group(1) if match else ""
            content = line[len(indent):].strip()
            # Collapse multiple inner spaces
            content = re.sub(r"[ \t]+", " ", content)
            compressed.append(indent + content)
        return "\n".join(compressed)
