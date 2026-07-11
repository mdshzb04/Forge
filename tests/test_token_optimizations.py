"""Unit tests for Forge token optimization features."""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from forgecli.optimizer.comment_stripper import CommentStripper
from forgecli.optimizer.token_estimator import TokenEstimator
from forgecli.optimizer.retrieval_cache import RetrievalCache
from forgecli.optimizer.embedding_cache import EmbeddingCache
from forgecli.build.patch_generator import PatchGenerator


def test_comment_stripper_python():
    code = (
        "# License header\n"
        "'''\nDocstring\n'''\n"
        "def foo():\n"
        "    # inline comment\n"
        "    x = 1  # end of line comment\n"
        "    return x\n"
    )
    # Off
    assert CommentStripper.strip_comments(code, "test.py", "off") == code

    # Lite
    lite = CommentStripper.strip_comments(code, "test.py", "lite")
    assert "inline comment" in lite
    assert "end of line comment" not in lite

    # Full
    full = CommentStripper.strip_comments(code, "test.py", "full")
    assert "Docstring" not in full
    assert "inline comment" not in full

    # Ultra
    ultra = CommentStripper.strip_comments(code, "test.py", "ultra")
    assert "Docstring" not in ultra
    assert "\n\n" not in ultra


def test_comment_stripper_c_style():
    code = (
        "// License header\n"
        "/* Multiline comment */\n"
        "function bar() {\n"
        "    // inline comment\n"
        "    let x = 1; // end of line comment\n"
        "    return x;\n"
        "}\n"
    )
    # Off
    assert CommentStripper.strip_comments(code, "test.js", "off") == code

    # Lite
    lite = CommentStripper.strip_comments(code, "test.js", "lite")
    assert "inline comment" in lite
    assert "end of line comment" not in lite

    # Full
    full = CommentStripper.strip_comments(code, "test.js", "full")
    assert "inline comment" not in full
    assert "Multiline comment" not in full


def test_token_estimator():
    text = "def hello(): print('hello world')"
    
    # Check tiktoken integration
    count_openai = TokenEstimator.estimate_tokens(text, "gpt-4o")
    assert count_openai > 0
    
    count_anthropic = TokenEstimator.estimate_tokens(text, "claude-3-5-sonnet")
    assert count_anthropic > 0
    
    # Check fallback detection
    count_llama = TokenEstimator.estimate_tokens(text, "llama-3-8b")
    assert count_llama > 0
    
    # Empty string
    assert TokenEstimator.estimate_tokens("", "gpt-4o") == 0


def test_retrieval_cache(tmp_path):
    db_path = tmp_path / "retrieval.db"
    cache = RetrievalCache(db_path, ttl_seconds=1.0)
    
    fingerprint = "hash1"
    cache.set("semantic_search", "key1", {"data": "val1"}, fingerprint)
    
    # Valid retrieval
    assert cache.get("semantic_search", "key1", fingerprint) == {"data": "val1"}
    
    # Invalidation by fingerprint change
    assert cache.get("semantic_search", "key1", "hash2") is None
    
    # Invalidation by TTL
    cache.set("semantic_search", "key1", {"data": "val1"}, fingerprint)
    time.sleep(1.1)
    assert cache.get("semantic_search", "key1", fingerprint) is None


def test_embedding_cache(tmp_path):
    db_path = tmp_path / "embeddings.db"
    cache = EmbeddingCache(db_path)
    
    model = "text-embedding-3-small"
    inputs = ["hello", "world"]
    
    cached, missing = cache.lookup(model, inputs)
    assert not cached
    assert missing == ["hello", "world"]
    
    # Save to cache
    vectors = {"hello": [0.1, 0.2], "world": [0.3, 0.4]}
    cache.save(model, vectors)
    
    # Exact lookup
    cached2, missing2 = cache.lookup(model, inputs)
    assert cached2 == vectors
    assert not missing2
    
    # Incremental lookup
    cached3, missing3 = cache.lookup(model, ["hello", "there"])
    assert cached3 == {"hello": [0.1, 0.2]}
    assert missing3 == ["there"]


def test_patch_generator(tmp_path):
    # Setup test file
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    original_code = "def start():\n    print('start')\n"
    file_path.write_text(original_code, encoding="utf-8")
    
    prompt = "Modify main.py to print hello instead"
    
    # 1. Output already a diff
    diff_text = "diff --git a/src/main.py b/src/main.py\n..."
    assert PatchGenerator.ensure_patch(diff_text, tmp_path, prompt) == diff_text
    
    # 2. Output is full file content (markdown fenced)
    new_code = "```python\ndef start():\n    print('hello')\n```"
    recovered_diff = PatchGenerator.ensure_patch(new_code, tmp_path, prompt)
    
    assert "print('start')" in recovered_diff or "-" in recovered_diff
    assert "print('hello')" in recovered_diff or "+" in recovered_diff


def test_context_compression():
    from forgecli.optimizer.compression import ContextCompressionEngine
    
    # Test duplicate imports
    import_text = (
        "import os\n"
        "import sys\n"
        "import os\n"
        "from typing import Any\n"
        "from typing import Any\n"
    )
    compressed_imports = ContextCompressionEngine.remove_duplicate_imports(import_text)
    assert compressed_imports.count("import os") == 1
    assert compressed_imports.count("from typing import Any") == 1
    
    # Test repeated diagnostics
    diag_text = (
        "Error: NullPointer\n"
        "Error: NullPointer\n"
        "Error: NullPointer\n"
        "warning: something went wrong\n"
    )
    compressed_diags = ContextCompressionEngine.remove_repeated_diagnostics(diag_text)
    assert "Repeated 2 times" in compressed_diags
    assert compressed_diags.count("Error: NullPointer") == 1

    # Test duplicate markdown code blocks
    md_text = (
        "```python\ndef run():\n    pass\n```\n"
        "Some text\n"
        "```python\ndef run():\n    pass\n```\n"
    )
    compressed_md = ContextCompressionEngine.remove_duplicate_markdown_blocks(md_text)
    assert "Duplicate code block" in compressed_md
    assert compressed_md.count("def run()") == 1

