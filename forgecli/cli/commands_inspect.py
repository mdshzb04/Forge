"""forge inspect — display the active pipeline, loaded plugins, provider, and optimization stages."""



from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.ui import get_console


def inspect_cmd(

    repo: Path | None = typer.Option(None, "--repo", "-r", help="Repository path to inspect."),

) -> None:

    """Display the active pipeline, loaded plugins, provider, Graphify status, and optimization stages."""

    console = get_console()

    cwd = (repo or Path.cwd()).resolve()



    console.print()

    console.print("  [bold cyan]Forge Runtime Inspection[/bold cyan]")

    console.print(f"  [dim]Repository: {cwd}[/dim]")

    console.print()









    console.print("  [bold]Middleware Pipeline[/bold]")

    console.print()



    from forgecli.middleware.defaults import (
        AuthenticationMiddleware,
        CachingMiddleware,
        ContextOptimizerMiddleware,
        ConversationMiddleware,
        DependencyGraphMiddleware,
        GraphifyMiddleware,
        HistoryCompressorMiddleware,
        PolicyMiddleware,
        PromptOptimizerMiddleware,
        ProviderMiddleware,
        RepositoryPlannerMiddleware,
        ResponseOptimizerMiddleware,
        SemanticRetrievalMiddleware,
        StreamingMiddleware,
        SymbolLookupMiddleware,
        TelemetryMiddleware,
        TokenPlannerMiddleware,
    )



    middlewares = [

        (TelemetryMiddleware(), "forgecli.observability.middleware"),

        (AuthenticationMiddleware(), "forgecli.middleware.defaults"),

        (PolicyMiddleware(), "forgecli.policy.middleware"),

        (CachingMiddleware(), "forgecli.memory.caching_middleware"),

        (HistoryCompressorMiddleware(), "forgecli.memory.middleware"),

        (TokenPlannerMiddleware(), "forgecli.budget.middleware"),

        (ContextOptimizerMiddleware(), "forgecli.budget.middleware"),

        (ConversationMiddleware(), "forgecli.middleware.defaults"),

        (PromptOptimizerMiddleware(), "forgecli.middleware.ponytail_adapter"),

        (RepositoryPlannerMiddleware(), "forgecli.middleware.defaults"),

        (DependencyGraphMiddleware(), "forgecli.middleware.defaults"),

        (SymbolLookupMiddleware(), "forgecli.middleware.defaults"),

        (GraphifyMiddleware(), "forgecli.middleware.graphify_adapter"),

        (SemanticRetrievalMiddleware(), "forgecli.middleware.defaults"),

        (StreamingMiddleware(), "forgecli.streaming.middleware"),

        (ProviderMiddleware(), "forgecli.middleware.defaults"),

        (ResponseOptimizerMiddleware(), "forgecli.middleware.defaults"),

    ]



    for mw, source in middlewares:

        status = "[green]active[/green]" if mw.enabled else "[yellow]disabled[/yellow]"

        console.print(

            f"    {mw.priority:>4}  {type(mw).__name__:<32}  {status}  [dim]{source}[/dim]"

        )





    from forgecli.middleware.caveman_adapter import CavemanAdapterMiddleware
    from forgecli.middleware.ponytail_adapter import PonytailAdapterMiddleware
    from forgecli.resilience.middleware import ResilienceMiddleware



    adapters = [

        (CavemanAdapterMiddleware(), "forgecli.middleware.caveman_adapter"),

        (PonytailAdapterMiddleware(), "forgecli.middleware.ponytail_adapter"),

        (ResilienceMiddleware(), "forgecli.resilience.middleware"),

    ]

    for mw, source in adapters:

        status = "[green]active[/green]" if mw.enabled else "[yellow]disabled[/yellow]"

        console.print(

            f"    {mw.priority:>4}  {type(mw).__name__:<32}  {status}  [dim]{source}[/dim]"

        )



    console.print()









    console.print("  [bold]Provider Status[/bold]")

    console.print()



    try:

        from forgecli.providers.base import default_registry

        provider_names = default_registry.names()

        for name in provider_names:

            api_configured = _check_api_key(name)

            key_status = "[green]configured[/green]" if api_configured else "[yellow]not configured[/yellow]"

            console.print(f"    {name:<16}  {key_status}  [dim]({name.upper()}_API_KEY)[/dim]")

    except Exception:

        console.print("    [dim]Provider registry not available.[/dim]")



    console.print()









    console.print("  [bold]Graphify Status[/bold]")

    console.print()



    try:

        from forgecli.graph.backend_forgegraph import ForgeRepositoryGraph

        graph = ForgeRepositoryGraph(root=cwd)

        available = _run_async(graph.is_available())

        if available:

            console.print("    [green]Available[/green] — graphifyy binary found")

            try:

                snapshot = _run_async(graph.load())

                node_count = len(snapshot.nodes)

                edge_count = len(snapshot.edges)

                console.print(f"    Nodes: {node_count}  Edges: {edge_count}")

            except Exception:

                console.print("    [dim]Graph not built yet. Run [cyan]forge graph build[/cyan][/dim]")

        else:

            console.print("    [yellow]Not available[/yellow] — install with [cyan]uv tool install graphifyy --with anthropic[/cyan]")

    except Exception:

        console.print("    [dim]Graphify backend not available.[/dim]")



    console.print()









    console.print("  [bold]Optimization Profiles[/bold]")

    console.print()



    try:

        from forgecli.config.loader import ConfigLoader

        loader = ConfigLoader()

        settings = loader.load()

        p_intensity = settings.prompt_optimizer.intensity if settings.prompt_optimizer.enabled else "off"

        c_intensity = settings.caveman.intensity if settings.caveman.enabled else "off"

        o_intensity = settings.output_optimization.intensity if settings.output_optimization.enabled else "off"

    except Exception:

        p_intensity = "lite"

        c_intensity = "lite"

        o_intensity = "lite"



    modes = {

        "off": "[dim]off[/dim]",

        "lite": "[yellow]lite[/yellow]",

        "full": "[green]full[/green]",

        "ultra": "[cyan]ultra[/cyan]",

        "wenyan": "[magenta]wenyan[/magenta]",

    }



    console.print(f"    Ponytail (prompt)  : {modes.get(p_intensity, p_intensity)}")

    console.print(f"    Caveman (output)   : {modes.get(c_intensity, c_intensity)}")

    console.print(f"    Output opt         : {modes.get(o_intensity, o_intensity)}")



    console.print()









    console.print("  [bold]Daemon Status[/bold]")

    console.print()



    import httpx

    try:

        with httpx.Client(timeout=2.0) as client:

            resp = client.get("http://127.0.0.1:16868/health")

            if resp.status_code == 200:

                console.print("    [green]Running[/green]  http://127.0.0.1:16868")

            else:

                console.print(f"    [yellow]Responding ({resp.status_code})[/yellow]  http://127.0.0.1:16868")

    except Exception:

        console.print("    [dim]Not running. Start with [cyan]forge start[/cyan][/dim]")



    console.print()









    console.print()





def _check_api_key(provider_name: str) -> bool:

    """Check if the API key env var is set for a provider."""

    import os

    env_map = {

        "openai": "OPENAI_API_KEY",

        "anthropic": "ANTHROPIC_API_KEY",

        "google": "GOOGLE_API_KEY",

        "openrouter": "OPENROUTER_API_KEY",

        "groq": "GROQ_API_KEY",

        "mistral": "MISTRAL_API_KEY",

        "cohere": "COHERE_API_KEY",

        "deepseek": "DEEPSEEK_API_KEY",

    }

    env_var = env_map.get(provider_name)

    if env_var:

        return bool(os.environ.get(env_var))

    return False





def _run_async(coro):

    """Run an async function synchronously."""

    import asyncio

    try:

        asyncio.get_running_loop()

    except RuntimeError:

        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:

        future = executor.submit(asyncio.run, coro)

        return future.result()

