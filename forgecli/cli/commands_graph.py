"""``forge graph`` subcommand group: build.

These commands integrate the external ForgeGraph CLI behind the
:mod:`forgecli.graph.repository` abstraction. When the binary is not
installed the commands print an installation hint instead of failing.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from forgecli.cli.ui import (
    error,
    get_console,
    info,
    success,
)
from forgecli.graph.backend_forgegraph import ForgeRepositoryGraph
from forgecli.utils.fs import has_supported_source_files
from forgecli.utils.paths import to_privacy_path

app = typer.Typer(
    help="Build the codebase graph.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _build_backend(path: Path) -> ForgeRepositoryGraph:

    return ForgeRepositoryGraph(root=path)


_PROVIDER_TO_BACKEND = {
    "google": "gemini",
    "gemini": "gemini",
    "anthropic": "claude",
    "claude": "claude",
    "openai": "openai",
    "deepseek": "deepseek",
    "groq": "openai",
    "openrouter": "openai",
    "mistral": "openai",
    "cohere": "openai",
}

# Providers whose API natively matches a graphify backend.
# For these, we do NOT pass --model and let graphify use its own defaults
# (e.g. claude-sonnet-4-6, gpt-4.1-mini, gemini-3-flash-preview).
_NATIVE_PROVIDERS = {"openai", "anthropic", "claude", "google", "gemini", "deepseek"}

# Model overrides ONLY for OpenAI-compat providers (groq, openrouter, etc.)
# where the upstream server needs a specific model name that differs from
# the Forge router's default model name.
_MODEL_OVERRIDE_MAP = {
    "llama-4-scout": "llama-3.1-70b-versatile",
    "glm-5.2": "meta-llama/llama-3.1-70b-instruct",
}


def _apply_openai_compat_overrides(provider_name: str, model: str) -> None:
    from forgecli.providers.router import _PROVIDER_ENV_VARS

    if provider_name in ("groq", "openrouter", "mistral", "cohere"):
        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "mistral": "https://api.mistral.ai/v1",
            "cohere": "https://api.cohere.ai/v1",
        }
        env_vars = _PROVIDER_ENV_VARS.get(provider_name, ())
        api_key = None
        for ev in env_vars:
            if os.environ.get(ev):
                api_key = os.environ[ev]
                break
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if provider_name in base_urls:
            os.environ["OPENAI_BASE_URL"] = base_urls[provider_name]

        mapped_model = _MODEL_OVERRIDE_MAP.get(model, model)
        os.environ["OPENAI_MODEL"] = mapped_model


def setup_forgegraph_credentials(
    path: Path, provider_override: str | None = None
) -> tuple[str, str] | None:
    """Read the active provider, load its API key, set env vars, and return (provider, model) if configured."""

    from forgecli.cli.bootstrap import bootstrap_context
    from forgecli.core.credentials import get_api_key
    from forgecli.providers.router import _PROVIDER_ENV_VARS, ModelRouter
    from forgecli.providers.router_state import load_state as load_router_state

    app_context = bootstrap_context(cwd=path)

    state = load_router_state(app_context.paths.data_dir / "router.json")

    router = app_context.container.resolve(ModelRouter)

    if provider_override:
        provider_name = router.resolve_alias(provider_override)
        model_name = router.default_model_for(provider_name)
    else:
        decision = router.select(state.choice)
        provider_name = decision.provider_name
        model_name = decision.model

    if provider_name != "mock":
        env_vars = _PROVIDER_ENV_VARS.get(provider_name, ())
        for ev in env_vars:
            if os.environ.get(ev):
                _apply_openai_compat_overrides(provider_name, model_name)
                return provider_name, model_name

        api_key = get_api_key(provider_name)
        if api_key:
            for ev in env_vars:
                os.environ[ev] = api_key
            _apply_openai_compat_overrides(provider_name, model_name)
            return provider_name, model_name

    # If provider override was requested but credentials are missing, we should NOT fallback to other providers
    if provider_override:
        return None

    # Fallback: scan other providers to see if the user exported any of their API keys
    for name, vars_tuple in _PROVIDER_ENV_VARS.items():
        if name == "mock":
            continue
        for ev in vars_tuple:
            if os.environ.get(ev):
                fallback_model = router.default_model_for(name)
                _apply_openai_compat_overrides(name, fallback_model)
                return name, fallback_model

    # Fallback 2: check if any provider has a saved key in the credentials store
    for name, vars_tuple in _PROVIDER_ENV_VARS.items():
        if name == "mock":
            continue
        api_key = get_api_key(name)
        if api_key:
            for ev in vars_tuple:
                os.environ[ev] = api_key
            fallback_model = router.default_model_for(name)
            _apply_openai_compat_overrides(name, fallback_model)
            return name, fallback_model

    return None


@app.command("build")
def build_cmd(
    path: str = typer.Option(".", "--path", "-p", help="Project root to index."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite graph.json even if the rebuild has fewer nodes.",
    ),
    no_cluster: bool = typer.Option(False, "--no-cluster", help="Skip Leiden clustering."),
    backend_opt: str | None = typer.Option(
        None,
        "--backend",
        help="AI backend to use for graph building (openai, claude, gemini, etc.).",
    ),
    model_opt: str | None = typer.Option(
        None,
        "--model",
        help="Model to use for graph building.",
    ),
) -> None:
    """Build (or rebuild) the codebase graph for ``path``."""

    import asyncio

    path_obj = Path(path).resolve()

    if not has_supported_source_files(path_obj):
        get_console().print("No supported source files found. Nothing to build.")

        raise typer.Exit(code=0)

    creds = setup_forgegraph_credentials(path_obj, provider_override=backend_opt)

    if not creds:
        get_console().print(
            "❌ API key required.\n\n"
            "Forge Graph requires an AI provider API key before a knowledge graph can be built."
        )

        raise typer.Exit(code=1)

    active_provider, active_model = creds

    backend_to_use = _PROVIDER_TO_BACKEND.get(active_provider, active_provider)

    # For native providers (openai, anthropic/claude, google/gemini, deepseek),
    # let graphify use its own built-in default model. Only override when:
    #   1. User explicitly passed --model on the CLI, OR
    #   2. Provider uses OpenAI-compat layer (groq, openrouter, etc.)
    #      and needs a specific model name the upstream server understands.
    is_native = active_provider in _NATIVE_PROVIDERS
    if model_opt:
        model_to_use = model_opt
    elif is_native:
        model_to_use = None  # let graphify pick the right default
    else:
        model_to_use = _MODEL_OVERRIDE_MAP.get(active_model, active_model)

    extra_args = []
    if backend_to_use:
        extra_args.extend(["--backend", backend_to_use])
    if model_to_use:
        extra_args.extend(["--model", model_to_use])

    backend = _build_backend(path_obj)

    async def _run() -> None:

        if not await backend.is_available():
            get_console().print(await backend.install_hint())

            raise typer.Exit(code=1)

        info(f"Building graph for [accent]{to_privacy_path(backend.root)}[/accent] ...")

        try:
            import json
            import time

            start_time = time.perf_counter()

            result = await backend.build(force=force, no_cluster=no_cluster, extra_args=extra_args)

            build_duration = time.perf_counter() - start_time

            try:
                build_time_file = backend.root / "forgegraph-out" / "build_time.json"

                build_time_file.parent.mkdir(parents=True, exist_ok=True)

                with open(build_time_file, "w", encoding="utf-8") as f:
                    json.dump({"build_time": build_duration}, f)

            except Exception:
                pass

            snapshot = result.snapshot

            get_console().print(
                f"  nodes:      [bold]{len(snapshot.nodes)}[/bold]\n"
                f"  edges:      [bold]{len(snapshot.edges)}[/bold]\n"
                f"  communities:[bold]{len(snapshot.communities)}[/bold]"
            )

            for label, value in result.artifacts.items():
                get_console().print(f"  [muted]{label}:[/muted] {to_privacy_path(value)}")

            success("Graph built.")

        except Exception as exc:
            error(f"Graph build failed: {exc}")

            raise typer.Exit(code=1) from exc

    try:
        asyncio.run(_run())

    except typer.Exit:
        raise

    except Exception as exc:
        error(f"Graph build failed: {exc}")

        raise typer.Exit(code=1) from exc


__all__ = ["app"]
