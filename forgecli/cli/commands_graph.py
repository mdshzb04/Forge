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

    if provider_name == "mock":

        return None





    env_vars = _PROVIDER_ENV_VARS.get(provider_name, ())

    for ev in env_vars:

        if os.environ.get(ev):

            return provider_name





    api_key = get_api_key(provider_name)

    if api_key:

        for ev in env_vars:

            os.environ[ev] = api_key

        return provider_name



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

            result = await backend.build(force=force, no_cluster=no_cluster)

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

