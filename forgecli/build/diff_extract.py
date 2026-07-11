r"""Stage 4 — diff extraction.

LLMs love to wrap their output in prose. We extract the largest
unified diff block from the response (looking for ``diff --git`` or
``--- a/`` / ``+++ b/`` markers) and store the cleaned text in
``context.diff_text``. If no diff is found, ``diff_text`` is empty and
downstream stages short-circuit.

We also strip Markdown code fences (``\`\`\`diff ... \`\`\``) before
searching, since the system prompt asks for a diff but real models
often wrap their output anyway.
"""



from __future__ import annotations



import re

from pathlib import Path



from forgecli.build import BuildContext



_GIT_DIFF_HEADER = re.compile(r"^diff --git ", re.MULTILINE)

_UNIFIED_HEADER = re.compile(r"^--- ", re.MULTILINE)

_DIFF_LINE = re.compile(r"^(?:--- |\+\+\+ |@@ | |\+|-)", re.MULTILINE)

_DIFF_OR_CONTEXT = re.compile(r"^(?:--- |\+\+\+ |@@ | |\+|-|index |new file |deleted file |similarity |rename |copy )", re.MULTILINE)

_FENCE_OPEN = re.compile(r"^\s*```(?:\w+)?\s*$")

_FENCE_CLOSE = re.compile(r"^\s*```\s*$")





def extract_diff(text: str) -> str:

    """Return the largest unified-diff substring in ``text``.

    The search is anchored to the first ``diff --git`` or ``--- a/`` header
    and runs to the first non-diff-looking line that follows a blank line
    or the end of the text. We deliberately keep this lenient: real
    models emit all kinds of surrounding chatter.
    """

    if not text:

        return ""

    text = _strip_code_fences(text)

    match = _GIT_DIFF_HEADER.search(text)

    if not match:

        match = _UNIFIED_HEADER.search(text)

    if not match:

        return ""

    candidate = text[match.start():]

    return _trim_to_diff_block(candidate)





def _strip_code_fences(text: str) -> str:

    r"""Drop a single pair of Markdown code fences wrapping the whole text.

    Many models emit fenced diffs (``\`\`\`diff\n<diff>\n\`\`\``); we strip
    those fences so the header-search below can find ``diff --git``
    directly. Multi-fence responses (e.g. fences inside fences) are
    left alone.
    """

    lines = text.splitlines()

    if not lines:

        return text

    if not _FENCE_OPEN.match(lines[0]):

        return text

                              

    for index in range(1, len(lines)):

        if _FENCE_CLOSE.match(lines[index]):

            return "\n".join(lines[1:index])

    return "\n".join(lines[1:])





def _trim_to_diff_block(candidate: str) -> str:

    """Trim trailing prose that is clearly not part of the diff.

    We keep the diff block intact (including context lines) and stop at
    the first blank or non-diff line that follows a substantive diff.
    """

    lines = candidate.splitlines()

    kept: list[str] = []

    for line in lines:

        if not kept and not line.strip():

            continue

        if not _DIFF_OR_CONTEXT.match(line) and not line.startswith("diff --git "):

                                                                 

            if kept:

                break

            continue

        kept.append(line)

    return "\n".join(kept).rstrip() + "\n"





def _looks_like_diff_line(line: str) -> bool:

    if _DIFF_LINE.match(line):

        return True

    if line.startswith("diff --git "):

        return True

    return bool(line.startswith("index "))





def is_file_requested(relative_path: str | Path, prompt: str, root_dir: Path) -> bool:

    """Return True if the file was explicitly requested by the user or already exists."""

    path_str = str(relative_path)

    if path_str.startswith("b/") or path_str.startswith("a/"):

        path_str = path_str[2:]



    full_path = root_dir / path_str

                                                                          

    if full_path.exists():

        return True



                                                     

    cleaned_prompt = re.sub(r'[^\w\s-]', ' ', prompt.lower())

    prompt_words = set(cleaned_prompt.split())



                          

    path_obj = Path(path_str)

    filename = path_obj.name.lower()

    stem = path_obj.stem.lower()



                                                                           

    cleaned_prompt_with_dashes = prompt.lower()

    if filename in cleaned_prompt_with_dashes or stem in cleaned_prompt_with_dashes:

        return True



    for part in path_obj.parts:

        part_lower = part.lower()

        if part_lower in cleaned_prompt_with_dashes:

            return True



                                                      

    stem_tokens = re.split(r'[_.-]', stem)

    for token in stem_tokens:

        if len(token) >= 2 and token in prompt_words:

            return True



                         

    has_test_in_prompt = any(w in prompt_words for w in ("test", "tests", "testing", "regression", "regressions", "assert"))

    has_test_in_file = any(t in filename for t in ("test", "regression", "spec"))

    if has_test_in_prompt and has_test_in_file:

        return True



                                                    

    if filename == "__init__.py":

        parent_name = path_obj.parent.name.lower()

        if parent_name in cleaned_prompt_with_dashes or any(t in prompt_words for t in re.split(r'[_.-]', parent_name)):

            return True



    return False





def filter_diff(diff_text: str, prompt: str, root_dir: Path) -> str:

    """Filter the diff_text to only contain blocks for requested or existing files."""

    if not diff_text:

        return ""



    blocks = []

    lines = diff_text.splitlines(keepends=True)



    current_block: list[str] = []

    i = 0

    while i < len(lines):

        line = lines[i]

        is_new_block = False

        if line.startswith("diff --git ") or (line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ ") and (

            not current_block or not current_block[0].startswith("diff --git ")

        )):

            is_new_block = True



        if is_new_block and current_block:

            blocks.append(current_block)

            current_block = []



        current_block.append(line)

        i += 1



    if current_block:

        blocks.append(current_block)



    filtered_blocks = []

    for block in blocks:

        block_text = "".join(block)



                                  

        new_path = None

        match = re.search(r"^\+\+\+\s+(?:b/)?(?P<path>[^\s\n]+)", block_text, re.MULTILINE)

        if match:

            new_path = match.group("path")

            if new_path == "/dev/null":

                                                

                old_match = re.search(r"^---\s+(?:a/)?(?P<path>[^\s\n]+)", block_text, re.MULTILINE)

                if old_match:

                    new_path = old_match.group("path")

        else:

                                           

            git_match = re.search(r"^diff --git\s+(?:a/[^\s]+)\s+b/(?P<path>[^\s\n]+)", block_text, re.MULTILINE)

            if git_match:

                new_path = git_match.group("path")



        if not new_path:

            filtered_blocks.append(block_text)

            continue



        if new_path.startswith("b/") or new_path.startswith("a/"):

            new_path = new_path[2:]



        if is_file_requested(new_path, prompt, root_dir):

            filtered_blocks.append(block_text)



    return "".join(filtered_blocks)





async def diff_extraction(context: BuildContext) -> BuildContext:

    """Extract a unified diff from ``context.response`` and store in ``diff_text``."""

    if context.response is None:

        return context

    extracted = extract_diff(context.response.message.content or "")

    context.diff_text = filter_diff(extracted, context.prompt, context.root)

    return context





__all__ = ["diff_extraction", "extract_diff", "filter_diff", "is_file_requested"]

