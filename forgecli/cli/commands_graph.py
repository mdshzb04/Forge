"""Forge graph command group."""
from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.ui import get_console, info, success
from forgecli.graph.local_engine import LocalCodeGraph

app = typer.Typer(help="Build and inspect Forge's local code graph.", no_args_is_help=False, rich_markup_mode="rich")


def _run_graph(path: str, force: bool) -> None:
    root = Path(path).resolve()
    engine = LocalCodeGraph(root)
    import asyncio

    async def _run() -> None:
        info(f"Building local graph for {root} ...")
        result = await engine.build(force=force)
        snapshot = result.snapshot
        success("Graph built")
        get_console().print(f"  files: [bold]{snapshot.metadata.get('files', len(snapshot.nodes))}[/bold]")
        get_console().print(f"  nodes: [bold]{len(snapshot.nodes)}[/bold]")
        get_console().print(f"  edges: [bold]{len(snapshot.edges)}[/bold]")
        snapshot_path = result.artifacts.get("snapshot")
        if snapshot_path:
            get_console().print(f"  snapshot: [bold]{snapshot_path}[/bold]")

    asyncio.run(_run())


@app.callback(invoke_without_command=True)
def graph_root(
    path: str = typer.Option(".", "--path", "-p", help="Project root to analyze."),
    force: bool = typer.Option(False, "--force", help="Rebuild the graph snapshot."),
) -> None:
    _run_graph(path, force)


@app.command("build")
def build_cmd(
    path: str = typer.Option(".", "--path", "-p", help="Project root to analyze."),
    force: bool = typer.Option(False, "--force", help="Rebuild the graph snapshot."),
) -> None:
    _run_graph(path, force)
