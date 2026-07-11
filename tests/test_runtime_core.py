"""Unit tests for Phase 1 of the Forge Universal AI Runtime implementation."""



from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest
from pydantic import ValidationError

from forgecli.runtime_core.config_manager import ConfigurationManager
from forgecli.runtime_core.errors import (
    ConfigurationError,
    ForgeError,
    PipelineError,
    PluginError,
    PolicyViolationError,
    ProviderError,
    SessionError,
)
from forgecli.runtime_core.request import AIRequest, FileContext
from forgecli.runtime_core.response import AIResponse, StreamingChunk


def test_forge_error_context() -> None:

    """Verify that ForgeError correctly formats context dictionary data."""

    err = ForgeError("Base error", {"code": 404, "target": "database"})

    assert err.message == "Base error"

    assert err.context == {"code": 404, "target": "database"}

    assert "Base error" in str(err)

    assert "Context:" in str(err)





def test_exception_subclasses() -> None:

    """Verify subclass identity and exception hierarchy."""

    exceptions = [

        (ConfigurationError, "Config fail"),

        (SessionError, "Session fail"),

        (PipelineError, "Pipeline fail"),

        (ProviderError, "Provider fail"),

        (PolicyViolationError, "Policy violation"),

        (PluginError, "Plugin lifecycle fail"),

    ]



    for exc_cls, msg in exceptions:

        inst = exc_cls(msg, {"detail": "debug"})

        assert isinstance(inst, ForgeError)

        assert inst.message == msg

        assert inst.context == {"detail": "debug"}













def test_file_context_validation() -> None:

    """Verify FileContext model validation constraints and parsing."""

    file_ctx = FileContext(

        filepath="src/main.py",

        content="print('hello')",

        hash_id="sha256hashid",

        is_modified=True,

    )

    assert file_ctx.filepath == "src/main.py"

    assert file_ctx.content == "print('hello')"

    assert file_ctx.hash_id == "sha256hashid"

    assert file_ctx.is_modified is True





    data = {"filepath": "a.py", "content": "1", "hash_id": "h", "extra_meta": 42}

    parsed = FileContext(**data)

    assert parsed.filepath == "a.py"



    assert parsed.__dict__.get("extra_meta") is None

    assert parsed.model_extra == {"extra_meta": 42}





def test_ai_request_validation() -> None:

    """Verify AIRequest model rules, constraints, and default values."""

    req = AIRequest(

        request_id="req-123",

        prompt="Explain inheritance",

        provider_name="anthropic",

        model_name="claude-3-5-sonnet",

        session_id="session-xyz",

    )

    assert req.request_id == "req-123"

    assert req.prompt == "Explain inheritance"

    assert req.temperature == 0.2

    assert req.stream is True

    assert req.attached_files == []





    with pytest.raises(ValidationError):

        AIRequest(

            request_id="r",

            prompt="p",

            provider_name="pr",

            model_name="m",

            session_id="s",

            temperature=-0.5,

        )



    with pytest.raises(ValidationError):

        AIRequest(

            request_id="r",

            prompt="p",

            provider_name="pr",

            model_name="m",

            session_id="s",

            temperature=2.5,

        )













def test_streaming_chunk_validation() -> None:

    """Verify StreamingChunk validation constraints."""

    chunk = StreamingChunk(

        chunk_id="chunk-0",

        request_id="req-123",

        delta_content="import ",

        latency_ms=12.5,

    )

    assert chunk.chunk_id == "chunk-0"

    assert chunk.delta_content == "import "

    assert chunk.latency_ms == 12.5

    assert chunk.finish_reason is None





    with pytest.raises(ValidationError):

        StreamingChunk(

            chunk_id="c",

            request_id="r",

            delta_content="d",

            latency_ms=-1.0,

        )





def test_ai_response_validation() -> None:

    """Verify AIResponse validation and usage structures."""

    resp = AIResponse(

        response_id="resp-1",

        request_id="req-123",

        content="Success",

        finish_reason="stop",

        latency_ms=150.3,

        token_usage={"input": 10, "output": 20},

    )

    assert resp.response_id == "resp-1"

    assert resp.content == "Success"

    assert resp.token_usage == {"input": 10, "output": 20}



    with pytest.raises(ValidationError):

        AIResponse(

            response_id="resp-1",

            request_id="req-123",

            content="Success",

            finish_reason="stop",

            latency_ms=-100.0,

        )













def test_config_manager_explicit_paths(tmp_path: Path) -> None:

    """Verify ConfigurationManager resolves specific path settings."""

    cfg_file = tmp_path / "custom.toml"

    cfg_file.write_text(

        '[app]\nname = "explicit-app"\nlog_level = "DEBUG"\n',

        encoding="utf-8",

    )



    manager = ConfigurationManager(cfg_file)

    settings = manager.get_settings()

    assert settings.app.name == "explicit-app"

    assert settings.app.log_level == "DEBUG"





def test_config_manager_invalid_toml_raises_configuration_error(tmp_path: Path) -> None:

    """Verify that ConfigurationManager wraps TOML loader errors."""

    bad_file = tmp_path / "bad.toml"

    bad_file.write_text("invalid = { string without closing", encoding="utf-8")



    manager = ConfigurationManager(bad_file)

    with pytest.raises(ConfigurationError) as exc_info:

        manager.get_settings()



    assert "Failed to load runtime configuration" in exc_info.value.message

    assert "original_error" in exc_info.value.context





def test_config_manager_precedence_merging(tmp_path: Path, monkeypatch) -> None:

    """Verify layered merging of config candidates and env overrides."""

    pyproject = tmp_path / "pyproject.toml"

    pyproject.write_text(

        '[tool.forgecli.app]\nname = "pyproject-app"\nlog_level = "DEBUG"\n',

        encoding="utf-8",

    )

    forge_toml = tmp_path / "Forge.toml"

    forge_toml.write_text(

        '[app]\nname = "forge-toml-app"\n',

        encoding="utf-8",

    )

    forgecli_toml = tmp_path / "forgecli.toml"

    forgecli_toml.write_text(

        '[app]\nname = "forgecli-toml-app"\n',

        encoding="utf-8",

    )





    monkeypatch.chdir(tmp_path)











    manager = ConfigurationManager()

    settings = manager.get_settings()



    assert settings.app.name == "forgecli-toml-app"

    assert settings.app.log_level == "DEBUG"





    monkeypatch.setenv("FORGECLI_APP__NAME", "env-override-app")

    manager.invalidate_cache()

    new_settings = manager.get_settings()

    assert new_settings.app.name == "env-override-app"





def test_config_manager_thread_safety(tmp_path: Path) -> None:

    """Verify thread safety during concurrent settings load and reload loops."""

    cfg_file = tmp_path / "config.toml"

    cfg_file.write_text('[app]\nname = "thread-safety-test"\n', encoding="utf-8")



    manager = ConfigurationManager(cfg_file)



    def load_task() -> str:

        settings = manager.get_settings()

        return settings.app.name



    def reload_task() -> None:

        manager.invalidate_cache()

        manager.get_settings(force_reload=True)





    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

        futures = []

        for i in range(50):

            if i % 5 == 0:

                futures.append(executor.submit(reload_task))

            else:

                futures.append(executor.submit(load_task))





        for fut in futures:

            fut.result()



    assert manager.get_settings().app.name == "thread-safety-test"

