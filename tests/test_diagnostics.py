"""Smoke tests for the diagnostics commands."""



from __future__ import annotations

from pathlib import Path


def test_cli_status(tmp_path: Path, monkeypatch) -> None:

    from typer.testing import CliRunner

    from forgecli.cli.main import app



    monkeypatch.chdir(tmp_path)

    runner = CliRunner()



    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0

    assert "Forge Status" in result.output

    assert "Repository" in result.output

    assert "Daemon" in result.output

    assert "Output Optimization" in result.output





def test_cli_doctor(tmp_path: Path, monkeypatch) -> None:

    from typer.testing import CliRunner

    from forgecli.cli.main import app



    monkeypatch.chdir(tmp_path)

    runner = CliRunner()



    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0

    assert "Forge Doctor" in result.output

    assert "Python" in result.output

    assert "Cache" in result.output

    assert "Configuration" in result.output

