"""``forge commit`` subcommand: generate and execute git commit based on staged diff."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import typer

from forgecli.cli.bootstrap import resolve_provider_and_decision
from forgecli.cli.ui import error, get_console, info, success
from forgecli.providers.base import ChatMessage, ChatRequest, Role


def commit_cmd(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation and commit immediately."
    ),
    live: bool = typer.Option(
        True,
        "--live/--no-live",
        help="Use a live AI provider. Set to false to use the mock provider.",
    ),
) -> None:
    """Generate a Conventional Commit message based on staged changes and commit them."""
    console = get_console()
    cwd = Path.cwd()

    # 1. Run git diff --cached to analyze staged changes.
    try:
        res = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        diff_text = res.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error(
            f"Failed to run 'git diff --cached'. Are you inside a Git repository?\nDetails: {exc.stderr}"
        )
        raise typer.Exit(code=1) from exc
    except FileNotFoundError as exc:
        error("Git command not found. Please install Git.")
        raise typer.Exit(code=1) from exc

    if not diff_text:
        error("No staged changes found. Use 'git add' to stage files before committing.")
        raise typer.Exit(code=1)

    # 2. Resolve provider and model decision.
    provider, decision = resolve_provider_and_decision(live=live, cwd=cwd)

    info(f"Analyzing staged changes using {decision.provider_name}/{decision.model}...")

    # 3. Generate prompt.
    system_prompt = (
        "You are an expert AI assistant that generates high-quality git commit messages.\n"
        "Your task is to analyze the provided git diff of staged changes and write a Conventional Commit message.\n\n"
        "Guidelines:\n"
        "1. Follow the Conventional Commits specification:\n"
        "   <type>(<optional scope>): <description>\n"
        "   Types: feat, fix, docs, refactor, perf, test, chore, style, build, ci, revert\n"
        "2. The description must be in imperative mood, present tense, and lowercase (e.g. 'add user service', not 'added user service').\n"
        "3. Keep the first line short, ideally under 70 characters.\n"
        "4. If the diff contains multiple independent changes or requires further explanation, you may add a body after one blank line.\n"
        "5. Output ONLY the commit message itself. Do not write any markdown code blocks, introductory text, or concluding text."
    )

    user_prompt = f"Here is the staged git diff:\n\n```diff\n{diff_text}\n```"

    request = ChatRequest(
        model=decision.model,
        messages=[
            ChatMessage(role=Role.SYSTEM, content=system_prompt),
            ChatMessage(role=Role.USER, content=user_prompt),
        ],
        temperature=0.2,
    )

    # 4. Invoke provider.
    try:
        response = asyncio.run(provider.chat(request))
        commit_message = response.message.content.strip()
    except Exception as exc:
        error(f"Failed to generate commit message from AI provider: {exc}")
        raise typer.Exit(code=1) from exc

    # Clean up markdown blocks if the provider wrapped it.
    if commit_message.startswith("```"):
        lines = commit_message.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        commit_message = "\n".join(lines).strip()

    if not commit_message:
        error("AI provider returned an empty commit message.")
        raise typer.Exit(code=1)

    # 5. Display suggested commit message and ask for confirmation.
    console.print()
    console.print("[bold cyan]Suggested commit message:[/bold cyan]")
    console.print("-" * 50)
    console.print(commit_message)
    console.print("-" * 50)
    console.print()

    if not yes and not typer.confirm("Do you want to commit with this message?"):
        info("Commit aborted.")
        raise typer.Exit(code=0)

    # 6. Execute git commit.
    try:
        subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=cwd)
        success("Changes successfully committed!")
    except subprocess.CalledProcessError as exc:
        error(f"Git commit failed: {exc}")
        raise typer.Exit(code=1) from exc
