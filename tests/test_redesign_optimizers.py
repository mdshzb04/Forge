"""Unit tests for redesigned context and token optimization runtime sub-systems."""



from __future__ import annotations

import tempfile
from pathlib import Path

from forgecli.memory.memory_compression import MemoryCompressionManager
from forgecli.optimizer.adaptive_budget import AdaptiveContextBudget
from forgecli.optimizer.ast_extractor import ASTExtractor
from forgecli.optimizer.compression import ContextCompressionEngine
from forgecli.optimizer.cost_estimator import TokenCostEstimator
from forgecli.optimizer.prompt_optimizer import PromptOptimizer
from forgecli.optimizer.quality_validation import QualityValidator
from forgecli.providers.base import ChatMessage, Role


def test_whitespace_collapsing() -> None:

    text = "hello   world \n\n\n  new   line"

    collapsed = ContextCompressionEngine.collapse_whitespace(text)

    assert collapsed == "hello world\nnew line"





def test_boilerplate_removal() -> None:

    text = "<!-- comment -->\n=====\nReal Content\n-----"

    cleaned = ContextCompressionEngine.remove_boilerplate(text)

    assert "Real Content" in cleaned

    assert "comment" not in cleaned

    assert "====" not in cleaned





def test_json_compression() -> None:

    raw = '{\n  "name": "Forge",\n  "empty_dict": {},\n  "empty_list": [],\n  "null_val": null,\n  "ok": true\n}'

    compressed = ContextCompressionEngine.compress_json(raw)

    assert compressed == '{"name":"Forge","ok":true}'





def test_python_ast_extractor() -> None:

    code = "import sys\n\ndef my_func():\n    return 'hello'\n\nclass MyClass:\n    pass"

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:

        f.write(code)

        f_path = Path(f.name)



    try:

        nodes = ASTExtractor.extract_nodes(f_path)

        names = {n.name for n in nodes}

        assert "my_func" in names

        assert "MyClass" in names

        assert "import" in names





        pruned = ASTExtractor.prune_file(f_path, {"my_func"})

        assert "my_func" in pruned

        assert "MyClass" not in pruned

        assert "sys" in pruned

    finally:

        f_path.unlink()





def test_js_ts_ast_extractor() -> None:

    code = "import { x } from 'y';\nclass A {}\nfunction b() {}\nconst c = () => {};"

    with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False) as f:

        f.write(code)

        f_path = Path(f.name)



    try:

        nodes = ASTExtractor.extract_nodes(f_path)

        names = {n.name for n in nodes}

        assert "A" in names

        assert "b" in names

        assert "c" in names

        assert "import" in names

    finally:

        f_path.unlink()





def test_adaptive_budget() -> None:

    config = AdaptiveContextBudget.get_budget_config("gemini-1.5-pro-thinking")

    assert config["max_context"] == 200000

    assert config["is_reasoning_model"] is True



    config_local = AdaptiveContextBudget.get_budget_config("ollama")

    assert config_local["max_context"] == 8000





def test_cost_estimator() -> None:

    tokens = TokenCostEstimator.estimate_tokens("The quick brown fox jumps over the lazy dog.")

    assert tokens > 0

    cost = TokenCostEstimator().estimate_cost("claude-3-5-sonnet", 1000, 500)

    assert cost > 0.0

    latency = TokenCostEstimator().estimate_latency("claude-3-5-sonnet", 1000, 500)

    assert latency > 0.0





def test_prompt_optimizer() -> None:

    opt = PromptOptimizer()

    cleaned = opt.optimize_user_prompt("Could you please write a function?")

    assert cleaned == "write a function?"



    sys_cleaned = opt.optimize_system_prompt("Do not return headers. Do not return headers.")

    assert sys_cleaned == "Do not return headers."





def test_memory_compression() -> None:

    mgr = MemoryCompressionManager(keep_recent_turns=2)

    history = [

        ChatMessage(role=Role.USER, content="Hello"),

        ChatMessage(role=Role.ASSISTANT, content="Hi"),

        ChatMessage(role=Role.USER, content="Task A"),

        ChatMessage(role=Role.ASSISTANT, content="Task A Done"),

    ]

    compressed = mgr.compress_history(history)



    assert len(compressed) == 3

    assert "User requested: Hello" in compressed[0].content





def test_quality_validation() -> None:

    valid_py = "def f():\n    pass"

    invalid_py = "def f(\n    pass"

    assert QualityValidator.validate_python_syntax(valid_py) is True

    assert QualityValidator.validate_python_syntax(invalid_py) is False



    valid_braces = "class A { void f() { } }"

    invalid_braces = "class A { void f() { }"

    assert QualityValidator.validate_braces_balance(valid_braces) is True

    assert QualityValidator.validate_braces_balance(invalid_braces) is False

