"""Tests for registry-driven MCP auto-configuration (JSON + TOML writers)."""



from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from forgecli.runtime import mcp_config
from forgecli.runtime.agents import AGENTS, AgentSpec, MCPTarget
from forgecli.runtime.mcp_config import (
    _write_json_mcp,
    _write_toml_mcp,
    configure_mcp_for_agent,
)


@pytest.fixture

def mock_mcp_entry(monkeypatch):

    monkeypatch.setattr(

        mcp_config, "get_forge_mcp_entry", lambda: {"command": "forge", "args": ["mcp"]}

    )





def test_write_json_mcp_creates_and_is_idempotent(tmp_path: Path, mock_mcp_entry) -> None:

    path = tmp_path / "nested" / "mcp.json"



    _write_json_mcp(path, "mcpServers")

    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["mcpServers"]["forge"] == {"command": "forge", "args": ["mcp"]}





    _write_json_mcp(path, "mcpServers")

    data2 = json.loads(path.read_text(encoding="utf-8"))

    assert list(data2["mcpServers"].keys()) == ["forge"]





def test_write_json_mcp_preserves_existing_servers(tmp_path: Path, mock_mcp_entry) -> None:

    path = tmp_path / "mcp.json"

    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")



    _write_json_mcp(path, "mcpServers")

    data = json.loads(path.read_text(encoding="utf-8"))

    assert "other" in data["mcpServers"]

    assert "forge" in data["mcpServers"]





def test_write_toml_mcp_creates_and_is_idempotent(tmp_path: Path, mock_mcp_entry) -> None:

    path = tmp_path / ".codex" / "config.toml"



    _write_toml_mcp(path, "mcp_servers")

    assert path.exists()

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))

    assert parsed["mcp_servers"]["forge"]["command"] == "forge"

    assert parsed["mcp_servers"]["forge"]["args"] == ["mcp"]



    before = path.read_text(encoding="utf-8")

    _write_toml_mcp(path, "mcp_servers")

    assert path.read_text(encoding="utf-8") == before





def test_write_toml_mcp_preserves_existing_content(tmp_path: Path, mock_mcp_entry) -> None:

    path = tmp_path / "config.toml"

    path.write_text('model = "gpt-5"\n', encoding="utf-8")



    _write_toml_mcp(path, "mcp_servers")

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))

    assert parsed["model"] == "gpt-5"

    assert "forge" in parsed["mcp_servers"]





def test_configure_mcp_for_agent_toml(tmp_path: Path, monkeypatch, mock_mcp_entry) -> None:

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    configure_mcp_for_agent(AGENTS["codex"], tmp_path)

    toml_path = tmp_path / ".codex" / "config.toml"

    assert toml_path.exists()

    assert "[mcp_servers.forge]" in toml_path.read_text(encoding="utf-8")





def test_configure_mcp_for_agent_codex_disables_github_when_no_token(tmp_path: Path, monkeypatch, mock_mcp_entry) -> None:

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    monkeypatch.delenv("GITHUB_PAT_TOKEN", raising=False)



    # Case 1: Config file doesn't have the section. It should append it as disabled.

    configure_mcp_for_agent(AGENTS["codex"], tmp_path)

    toml_path = tmp_path / ".codex" / "config.toml"

    assert toml_path.exists()

    content = toml_path.read_text(encoding="utf-8")

    assert '[plugins."github@openai-curated"]' in content

    assert 'enabled = false' in content



    # Case 2: Config file has the section enabled. It should change it to disabled.

    toml_path.write_text('[plugins."github@openai-curated"]\nenabled = true\n', encoding="utf-8")

    configure_mcp_for_agent(AGENTS["codex"], tmp_path)

    content2 = toml_path.read_text(encoding="utf-8")

    assert '[plugins."github@openai-curated"]' in content2

    assert 'enabled = false' in content2

    assert 'enabled = true' not in content2



    # Case 3: GITHUB_PAT_TOKEN is set. It should not disable it.

    monkeypatch.setenv("GITHUB_PAT_TOKEN", "some_token")

    toml_path.write_text('[plugins."github@openai-curated"]\nenabled = true\n', encoding="utf-8")

    configure_mcp_for_agent(AGENTS["codex"], tmp_path)

    content3 = toml_path.read_text(encoding="utf-8")

    assert '[plugins."github@openai-curated"]' in content3

    assert 'enabled = true' in content3

    assert 'enabled = false' not in content3







def test_configure_mcp_for_agent_skips_when_unsupported(tmp_path: Path, monkeypatch) -> None:

    monkeypatch.setattr(Path, "home", lambda: tmp_path)



    # Build a minimal AgentSpec with no MCP targets (supports_mcp=False)

    from forgecli.runtime.agents import AgentSpec

    no_mcp_agent = AgentSpec(

        id="test-no-mcp",

        name="Test No MCP",

        binary="test-no-mcp",

        install_hint="",

        mcp_targets=(),

        supports_mcp=False,

    )

    configure_mcp_for_agent(no_mcp_agent, tmp_path)

    assert not any(tmp_path.iterdir())





def test_get_forge_mcp_entry_shutil_finds_bin(monkeypatch) -> None:

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/forge")

    entry = mcp_config.get_forge_mcp_entry()

    assert entry["command"] == str(Path("/usr/bin/forge").resolve())

    assert entry["args"] == ["mcp"]





def test_get_forge_mcp_entry_fallback_to_python(monkeypatch) -> None:

    monkeypatch.setattr("shutil.which", lambda name: None)

    entry = mcp_config.get_forge_mcp_entry()

    import sys



    assert entry["command"] == sys.executable

    assert entry["args"] == ["-m", "forgecli.cli.main", "mcp"]





def test_all_agents_registered() -> None:

    assert set(AGENTS) == {"claude", "codex", "cursor", "antigravity"}

    for spec in AGENTS.values():

        assert isinstance(spec, AgentSpec)

        for target in spec.mcp_targets:

            assert isinstance(target, MCPTarget)

            assert target.fmt in {"json", "toml"}

            assert target.base in {"home", "repo"}





def test_run_mcp_stdio_prepends_behavior_instructions(monkeypatch) -> None:

    import io
    import sys

    from forgecli.cli import daemon



    monkeypatch.delenv("FORGE_CONTEXT", raising=False)

    monkeypatch.setattr(daemon, "is_daemon_running", lambda: True)



    class MockResponse:

        def json(self):

            return {"markdown": "### Raw Repo Context"}



    class MockClient:

        def __enter__(self):

            return self

        def __exit__(self, exc_type, exc_val, exc_tb):

            pass

        def get(self, url, **kwargs):

            return MockResponse()



    monkeypatch.setattr(daemon, "_get_httpx", lambda: type("MockHttpx", (), {"Client": lambda **k: MockClient()}))



    req = {

        "jsonrpc": "2.0",

        "id": 1,

        "method": "tools/call",

        "params": {

            "name": "get_optimized_context",

            "arguments": {"path": "/dummy/path", "query": "hello"}

        }

    }

    mock_stdin = io.StringIO(json.dumps(req) + "\n")

    mock_stdout = io.StringIO()



    monkeypatch.setattr(sys, "stdin", mock_stdin)

    monkeypatch.setattr(sys, "stdout", mock_stdout)



    monkeypatch.setattr(

        "forgecli.runtime.prepare.build_behavior_instructions",

        lambda: "=== SYSTEM INSTRUCTION ===\nPromptForge responseforge rules"

    )



    daemon.run_mcp_stdio()



    mock_stdout.seek(0)

    res_line = mock_stdout.readline()

    assert res_line

    res = json.loads(res_line)



    assert "result" in res

    content = res["result"]["content"][0]["text"]

    assert "=== SYSTEM INSTRUCTION ===" in content

    assert "### Raw Repo Context" in content



