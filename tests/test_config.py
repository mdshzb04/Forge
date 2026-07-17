"""Smoke tests for the configuration loader."""



from __future__ import annotations

from pathlib import Path

from forgecli.config.loader import ConfigLoader
from forgecli.config.settings import ForgeSettings


def test_loader_returns_default_settings_when_no_file(tmp_path: Path) -> None:

    loader = ConfigLoader(tmp_path / "missing.toml")

    settings = loader.load()

    assert isinstance(settings, ForgeSettings)

    assert settings.app.name == "forgecli"





def test_loader_reads_explicit_toml(tmp_path: Path) -> None:

    config_path = tmp_path / "forgecli.toml"

    config_path.write_text(

        '[app]\nname = "myapp"\nlog_level = "DEBUG"\n',

        encoding="utf-8",

    )

    settings = ConfigLoader(config_path).load()

    assert settings.app.name == "myapp"

    assert settings.app.log_level == "DEBUG"





def test_loader_merges_pyproject_section(tmp_path: Path) -> None:

    pyproject = tmp_path / "pyproject.toml"

    pyproject.write_text(

        '[tool.forgecli.app]\nname = "pp"\n',

        encoding="utf-8",

    )

    settings = ConfigLoader(pyproject).load()

    assert settings.app.name == "pp"





def test_cli_config_shows_help_and_values(tmp_path: Path, monkeypatch) -> None:

    from typer.testing import CliRunner

    from forgecli.cli.main import app



    monkeypatch.chdir(tmp_path)

    runner = CliRunner()





    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0

    assert "Forge Configuration" in result.output

    assert "PromptForge Profile : lite" in result.output

    assert "ResponseForge Profile  : lite" in result.output

    assert "Output Profile   : lite" in result.output





def test_cli_config_updates_profiles(tmp_path: Path, monkeypatch) -> None:

    import tomllib

    from typer.testing import CliRunner

    from forgecli.cli.main import app



    monkeypatch.chdir(tmp_path)

    runner = CliRunner()



    result = runner.invoke(

        app, ["config", "--promptforge", "ultra", "--responseforge", "full", "--output", "ultra"]

    )

    assert result.exit_code == 0

    assert "Config updated in" in result.output





    config_file = tmp_path / "forgecli.toml"

    assert config_file.exists()



    data = tomllib.loads(config_file.read_text(encoding="utf-8"))

    assert data["prompt_optimizer"]["intensity"] == "ultra"

    assert data["prompt_optimizer"]["enabled"] is True

    assert data["responseforge"]["intensity"] == "full"

    assert data["responseforge"]["enabled"] is True

    assert data["output_optimization"]["intensity"] == "ultra"

    assert data["output_optimization"]["enabled"] is True





    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0

    assert "PromptForge Profile : ultra" in result.output

    assert "ResponseForge Profile  : full" in result.output

    assert "Output Profile   : ultra" in result.output





def test_cli_config_invalid_fallback(tmp_path: Path, monkeypatch) -> None:

    import tomllib

    from typer.testing import CliRunner

    from forgecli.cli.main import app



    monkeypatch.chdir(tmp_path)

    runner = CliRunner()



    result = runner.invoke(

        app, ["config", "--promptforge", "invalid", "--responseforge", "wrong", "--output", "bad"]

    )

    assert result.exit_code == 0

    assert "Invalid PromptForge mode" in result.output

    assert "Invalid ResponseForge mode" in result.output

    assert "Invalid Output mode" in result.output

    assert "Config updated in" in result.output



    config_file = tmp_path / "forgecli.toml"

    assert config_file.exists()



    data = tomllib.loads(config_file.read_text(encoding="utf-8"))

    assert data["prompt_optimizer"]["intensity"] == "lite"

    assert data["responseforge"]["intensity"] == "lite"

    assert data["output_optimization"]["intensity"] == "lite"

