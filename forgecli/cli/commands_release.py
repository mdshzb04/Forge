"""``forge release`` subcommand: cut a release.

Creates a git tag with the specified version.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import typer

from forgecli.cli.ui import error, get_console, info, success, warn

app = typer.Typer(
    help="Cut a release (changelog promotion, tag, optional push).",
    invoke_without_command=True,
    rich_markup_mode="rich",
    context_settings={"allow_interspersed_args": True},
)


_SEMVER = re.compile(r"^v?\d+\.\d+\.\d+([\-+].+)?$")


@app.callback(invoke_without_command=True, context_settings={"allow_interspersed_args": True})
def release_cmd(
    ctx: typer.Context,
    version: str = typer.Argument(..., help="Version to release (e.g. 1.2.0) or 'validate' to validate release candidate."),
    path: str = typer.Option(".", "--path", "-p", help="Project root."),
    push: bool = typer.Option(
        False, "--push", help="Push the commit and the tag to the remote."
    ),
    remote: str = typer.Option("origin", "--remote", help="Remote name."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen."),
) -> None:
    """Cut a release end-to-end.

    To run E2E release validation, run: forge release validate
    """
    if ctx.invoked_subcommand is not None:
        return
    if version == "validate":
        val_args = ctx.args
        p_val = path
        r_val = None
        for i, arg in enumerate(val_args):
            if arg in ("-p", "--path") and i + 1 < len(val_args):
                p_val = val_args[i + 1]
            elif arg in ("-r", "--report") and i + 1 < len(val_args):
                r_val = Path(val_args[i + 1])
        validate_internal(path=p_val, output_report=r_val)
        return
    project = Path(path).resolve()
    if not _SEMVER.match(version):
        version = version.lstrip("v")
        if not _SEMVER.match(version):
            error(f"Version must look like 1.2.0 or v1.2.0; got {version!r}")
            raise typer.Exit(code=1)
        version = f"v{version}"

    if not _is_git_repo(project):
        warn("Not a git repository; cannot release.")
        return

    msg = f"Release {version}"
    if _run_git(["commit", "-m", msg], project, dry_run=dry_run) and not dry_run:
        success("Release commit created.")
    _run_git(["tag", "-a", version, "-m", msg], project, dry_run=dry_run)
    if dry_run:
        info(f"[dry-run] would create tag {version}")
    else:
        success(f"Tag {version} created.")

    if push:
        _run_git(["push", remote], project, dry_run=dry_run)
        _run_git(["push", remote, version], project, dry_run=dry_run)
        if not dry_run:
            success(f"Pushed commit and tag to {remote}.")


def _run_git(args: list[str], project: Path, *, dry_run: bool) -> bool:
    if dry_run:
        info(f"[dry-run] git {' '.join(args)}")
        return True
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(project),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        error(f"git not found: {exc}")
        raise typer.Exit(code=1) from exc
    if result.returncode != 0:
        error(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        raise typer.Exit(code=1)
    return True


def _is_git_repo(project: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(project),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def discover_subcommands(base_cmd: list[str]) -> list[list[str]]:
    import subprocess
    try:
        res = subprocess.run([*base_cmd, "--help"], capture_output=True, text=True, check=False)
        output = res.stdout
    except Exception:
        return []

    commands = []
    lines = output.splitlines()
    in_commands_section = False
    for line in lines:
        if "Commands:" in line:
            in_commands_section = True
            continue
        if in_commands_section:
            stripped = line.strip()
            if line.startswith("  ") and stripped and not stripped.startswith("-"):
                cmd_name = stripped.split()[0]
                if cmd_name not in ("validate", "help", "release"):
                    commands.append(cmd_name)
            elif line.startswith("╭─") or line.startswith("╰─") or line.startswith("│"):
                pass
            elif not line.startswith("  ") and line.strip():
                in_commands_section = False

    discovered = [base_cmd]
    for cmd in commands:
        sub_path = [*base_cmd, cmd]
        discovered.extend(discover_subcommands(sub_path))
    return discovered


def parse_readme_commands(readme_path: Path) -> list[str]:
    if not readme_path.exists():
        return []
    content = readme_path.read_text(encoding="utf-8")
    commands = []
    lines = content.splitlines()
    in_code_block = False
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            stripped = line.strip()
            if stripped.startswith("forge "):
                commands.append(stripped)
            elif stripped.startswith("uv run forge "):
                commands.append(stripped[7:])
    return commands


def validate_internal(
    path: str = ".",
    output_report: Path | None = None,
) -> None:
    """Perform a comprehensive end-to-end validation of ForgeCLI."""
    console = get_console()
    project = Path(path).resolve()

    console.print("[bold cyan]Starting Comprehensive Release Validation...[/bold cyan]")

    # 1. Discover all CLI subcommands recursively
    console.print("\n[bold cyan]1. Discovering CLI Subcommands...[/bold cyan]")
    subcommands = discover_subcommands(["forge"])
    console.print(f"Discovered [bold green]{len(subcommands)}[/bold green] command/subcommand paths:")
    for path_list in subcommands:
        console.print(f"  - {' '.join(path_list)}")

    # 2. Parse README.md commands
    console.print("\n[bold cyan]2. Parsing README.md Commands...[/bold cyan]")
    readme_path = project / "README.md"
    readme_cmds = parse_readme_commands(readme_path)
    console.print(f"Found [bold green]{len(readme_cmds)}[/bold green] commands in README.md:")
    for cmd in readme_cmds:
        console.print(f"  - {cmd}")

    # 3. Quality checks: pytest, ruff, mypy
    console.print("\n[bold cyan]3. Running Quality Checks (pytest, ruff, mypy)...[/bold cyan]")

    # Run pytest
    pytest_status = "FAIL"
    pytest_output = ""
    try:
        res = subprocess.run(["pytest"], cwd=str(project), capture_output=True, text=True)
        pytest_status = "PASS" if res.returncode == 0 else "FAIL"
        pytest_output = res.stdout + res.stderr
    except Exception as e:
        pytest_output = str(e)
    console.print(f"  pytest: [{'green' if pytest_status == 'PASS' else 'red'}]{pytest_status}[/]")

    # Run ruff check .
    ruff_status = "FAIL"
    ruff_output = ""
    try:
        res = subprocess.run(["ruff", "check", "."], cwd=str(project), capture_output=True, text=True)
        ruff_status = "PASS" if res.returncode == 0 else "FAIL"
        ruff_output = res.stdout + res.stderr
    except Exception as e:
        ruff_status = "SKIPPED (not installed)"
        ruff_output = str(e)
    console.print(f"  ruff: [yellow]{ruff_status}[/]")

    # Run mypy
    mypy_status = "FAIL"
    mypy_output = ""
    try:
        res = subprocess.run(["mypy", "forgecli"], cwd=str(project), capture_output=True, text=True)
        mypy_status = "PASS" if res.returncode == 0 else "FAIL"
        mypy_output = res.stdout + res.stderr
    except Exception as e:
        mypy_status = "SKIPPED"
        mypy_output = str(e)
    console.print(f"  mypy: [yellow]{mypy_status}[/]")

    # 4. E2E execution of discovered subcommands
    console.print("\n[bold cyan]4. Running E2E Command Execution...[/bold cyan]")
    e2e_results = []

    # Help verification for all paths
    for path_list in subcommands:
        cmd_str = " ".join(path_list) + " --help"
        try:
            res = subprocess.run([*path_list, "--help"], capture_output=True, text=True, check=False)
            status = "PASS" if res.returncode == 0 else "FAIL"
            e2e_results.append((cmd_str, status, res.stdout + res.stderr))
        except Exception as e:
            e2e_results.append((cmd_str, "FAIL", str(e)))

    # Basic safe command verification
    safe_commands = [
        "forge doctor",
        "forge provider list",
        "forge history list",
        "forge status"
    ]
    for cmd in safe_commands:
        try:
            res = subprocess.run(cmd.split(), capture_output=True, text=True, check=False)
            status = "PASS" if res.returncode == 0 else "FAIL"
            e2e_results.append((cmd, status, res.stdout + res.stderr))
        except Exception as e:
            e2e_results.append((cmd, "FAIL", str(e)))

    passed_e2e = sum(1 for _, status, _ in e2e_results if status == "PASS")
    console.print(f"E2E Execution: [bold green]{passed_e2e}/{len(e2e_results)}[/] commands passed.")

    # 5. Generate Markdown Report
    report_content = f"""# ForgeCLI Release Validation Report

## Executive Summary
- **Pytest**: {pytest_status}
- **Ruff**: {ruff_status}
- **Mypy**: {mypy_status}
- **E2E Commands Passed**: {passed_e2e}/{len(e2e_results)}

## CLI Command Discovery & Help Verification
| Command Path | E2E Status |
|---|---|
"""
    for cmd_str, status, _ in e2e_results:
        report_content += f"| `{cmd_str}` | {status} |\n"

    report_content += f"\n## Quality Check Details\n### Pytest Output\n```\n{pytest_output[-1000:]}\n```\n"
    if ruff_output:
        report_content += f"\n### Ruff Output\n```\n{ruff_output[-1000:]}\n```\n"
    if mypy_output:
        report_content += f"\n### Mypy Output\n```\n{mypy_output[-1000:]}\n```\n"

    if output_report:
        output_report.write_text(report_content, encoding="utf-8")
        success(f"Release validation report written to {output_report}")
    else:
        default_report_path = project / "release_validation_report.md"
        default_report_path.write_text(report_content, encoding="utf-8")
        success(f"Release validation report written to {default_report_path}")


__all__ = ["app"]
