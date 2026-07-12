"""``forge auth`` subcommand group: login."""

from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.bootstrap import bootstrap_context
from forgecli.cli.ui import error, get_console, info, success
from forgecli.core.credentials import set_api_key
from forgecli.providers.router import ModelRouter
from forgecli.providers.router_state import load_state, save_state
from forgecli.utils.paths import ProjectPaths

app = typer.Typer(
    help="Authenticate and configure AI providers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.command("login")
def login_cmd() -> None:
    """Interactively select a provider, enter an API key, and configure active defaults."""
    console = get_console()

    providers = [
        "google",
        "anthropic",
        "openai",
        "openrouter",
        "groq",
        "mistral",
        "cohere",
        "deepseek",
    ]

    console.print("\n[bold]Select an AI provider to configure:[/bold]\n")
    for idx, p in enumerate(providers, 1):
        console.print(f"  [cyan]{idx}[/cyan]. {p}")
    console.print()

    try:
        selection = typer.prompt("Enter the number or name of the provider", default="1")
    except typer.Abort:
        info("Cancelled.")
        raise typer.Exit(code=1) from None

    provider = ""
    # Parse choice
    selection_clean = selection.strip().lower()
    if selection_clean.isdigit():
        idx = int(selection_clean) - 1
        if 0 <= idx < len(providers):
            provider = providers[idx]
    elif selection_clean in providers:
        provider = selection_clean

    if not provider:
        error(f"Invalid selection: {selection}")
        raise typer.Exit(code=1)

    try:
        api_key = typer.prompt(
            f"Enter API key for {provider}",
            hide_input=True,
        )
    except typer.Abort:
        info("Cancelled.")
        raise typer.Exit(code=1) from None

    if not api_key.strip():
        error("API key cannot be empty.")
        raise typer.Exit(code=1)

    try:
        set_api_key(provider, api_key)
        success(f"Successfully saved API key for {provider}.")
    except Exception as exc:
        error(f"Failed to save API key: {exc}")
        raise typer.Exit(code=1) from exc

    # Check if the user wants to set this provider as default
    try:
        make_default = typer.confirm(
            f"Do you want to set '{provider}' as your active default provider?",
            default=True,
        )
    except typer.Abort:
        make_default = False

    if make_default:
        try:
            paths = ProjectPaths.from_env()
            router_json = paths.data_dir / "router.json"
            state = load_state(router_json)

            # Resolve default model using ModelRouter
            app_context = bootstrap_context(cwd=Path.cwd())
            router = app_context.container.resolve(ModelRouter)
            default_model = router.default_model_for(provider)

            state.choice = provider
            state.provider = provider
            state.model = default_model

            save_state(router_json, state)
            success(f"Set '{provider}' ({default_model}) as the active default provider.")
        except Exception as exc:
            error(f"Failed to set default provider in configuration: {exc}")
            raise typer.Exit(code=1) from exc
