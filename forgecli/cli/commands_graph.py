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

_MODEL_OVERRIDE_MAP = {
    "gpt-5": "gpt-4o-mini",
    "gpt-5-mini": "gpt-4o-mini",
    "gpt-4.1": "gpt-4o",
    "gpt-4.1-mini": "gpt-4o-mini",
    "claude-opus-4.8": "claude-3-5-sonnet-latest",
    "claude-opus-4.6": "claude-3-5-sonnet-latest",
    "claude-sonnet-4.6": "claude-3-5-sonnet-latest",
    "claude-sonnet-4.5": "claude-3-5-sonnet-latest",
    "claude-haiku-4.5": "claude-3-5-haiku-latest",
    "gemini-2.5-pro": "gemini-1.5-pro",
    "gemini-2.5-flash": "gemini-1.5-flash",
    "gemini-2.5-flash-lite": "gemini-1.5-flash",
    "gemini-2.0-flash": "gemini-1.5-flash",
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


def setup_forgegraph_credentials(path: Path) -> str | None:

    """Read the active provider, load its API key, set env vars, and return provider name if configured."""

    from forgecli.cli.bootstrap import bootstrap_context
    from forgecli.core.credentials import get_api_key
    from forgecli.providers.router import _PROVIDER_ENV_VARS, ModelRouter
    from forgecli.providers.router_state import load_state as load_router_state



    app_context = bootstrap_context(cwd=path)

    state = load_router_state(app_context.paths.data_dir / "router.json")

    router = app_context.container.resolve(ModelRouter)

    decision = router.select(state.choice)



    provider_name = decision.provider_name
    if provider_name != "mock":
        env_vars = _PROVIDER_ENV_VARS.get(provider_name, ())
        for ev in env_vars:
            if os.environ.get(ev):
                _apply_openai_compat_overrides(provider_name, decision.model)
                return provider_name

        api_key = get_api_key(provider_name)
        if api_key:
            for ev in env_vars:
                os.environ[ev] = api_key
            _apply_openai_compat_overrides(provider_name, decision.model)
            return provider_name

    # Fallback: scan other providers to see if the user exported any of their API keys
    for name, vars_tuple in _PROVIDER_ENV_VARS.items():
        if name == "mock":
            continue
        for ev in vars_tuple:
            if os.environ.get(ev):
                _apply_openai_compat_overrides(name, router.default_model_for(name))
                return name

    # Fallback 2: check if any provider has a saved key in the credentials store
    for name, vars_tuple in _PROVIDER_ENV_VARS.items():
        if name == "mock":
            continue
        api_key = get_api_key(name)
        if api_key:
            for ev in vars_tuple:
                os.environ[ev] = api_key
            _apply_openai_compat_overrides(name, router.default_model_for(name))
            return name

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

) -> None:

    """Build (or rebuild) the codebase graph for ``path``."""

    import asyncio



    path_obj = Path(path).resolve()





    if not has_supported_source_files(path_obj):

        get_console().print("No supported source files found. Nothing to build.")

        raise typer.Exit(code=0)





    active_provider = setup_forgegraph_credentials(path_obj)

    if not active_provider:

        get_console().print(

            "❌ API key required.\n\n"

            "Forge Graph requires an AI provider API key before a knowledge graph can be built."

        )

        raise typer.Exit(code=1)



    from forgecli.cli.bootstrap import bootstrap_context
    from forgecli.providers.router import ModelRouter
    from forgecli.providers.router_state import load_state as load_router_state

    app_context = bootstrap_context(cwd=path_obj)
    state = load_router_state(app_context.paths.data_dir / "router.json")
    router = app_context.container.resolve(ModelRouter)
    decision = router.select(state.choice)

    backend_to_use = _PROVIDER_TO_BACKEND.get(active_provider, active_provider)
    model_to_use = _MODEL_OVERRIDE_MAP.get(decision.model, decision.model)

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

