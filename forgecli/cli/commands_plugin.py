"""forge plugin install | list | remove | enable | disable | info | doctor

Manage ForgeCLI plugins from the marketplace.
"""



from __future__ import annotations

from pathlib import Path

import typer

from forgecli.cli.ui import error, get_console, info, success
from forgecli.sdk.manager import (
    PluginAlreadyInstalledError,
    PluginCompatibilityError,
    PluginError,
    PluginManager,
    PluginNotFoundError,
)

plugin_app = typer.Typer(name="plugin", help="Manage ForgeCLI plugins.")





@plugin_app.command("list")

def list_plugins() -> None:

    """List all installed plugins with status."""

    manager = PluginManager()

    plugins = manager.list()



    if not plugins:

        info("No plugins installed.")

        return



    console = get_console()

    console.print()

    console.print("  [bold cyan]Installed Plugins[/bold cyan]")

    console.print()



    for state, _loaded in plugins:

        status_color = "green" if state.enabled else "yellow"

        status_text = "enabled" if state.enabled else "disabled"

        version = state.version if state.version else "unknown"

        source = state.source if state.source else "filesystem"



        console.print(

            f"  [bold]{state.name}[/bold]  [{status_color}]{status_text}[/{status_color}]  "

            f"[dim]v{version}[/dim]  [dim]({source})[/dim]"

        )



    console.print()





@plugin_app.command("install")

def install_plugin(

    source: str = typer.Argument(..., help="Plugin source path or name"),

    from_git: str | None = typer.Option(None, "--git", help="Install from a git URL"),

) -> None:

    """Install a plugin from a local path or git URL."""

    manager = PluginManager()



    try:

        if from_git:

            plugin_obj = manager.install(source, from_git=from_git)

        else:

            path = Path(source).resolve()

            if not path.exists():

                error(f"Plugin source not found: {source}")

                raise typer.Exit(code=1)

            plugin_obj = manager.install(str(path), from_path=path)



        name = getattr(plugin_obj, "name", source)

        success(f"Installed plugin: {name}")

    except PluginAlreadyInstalledError as e:

        error(str(e))

        raise typer.Exit(code=1) from e

    except PluginCompatibilityError as e:

        error(str(e))

        raise typer.Exit(code=1) from e

    except PluginError as e:

        error(str(e))

        raise typer.Exit(code=1) from e





@plugin_app.command("remove")

def remove_plugin(

    name: str = typer.Argument(..., help="Plugin name to uninstall"),

    keep_files: bool = typer.Option(False, "--keep-files", help="Keep plugin files on disk"),

) -> None:

    """Uninstall a plugin."""

    manager = PluginManager()



    try:

        manager.uninstall(name, remove_files=not keep_files)

        success(f"Uninstalled plugin: {name}")

    except PluginNotFoundError as e:

        error(str(e))

        raise typer.Exit(code=1) from e

    except PluginError as e:

        error(str(e))

        raise typer.Exit(code=1) from e





@plugin_app.command("enable")

def enable_plugin(

    name: str = typer.Argument(..., help="Plugin name to enable"),

) -> None:

    """Enable an installed plugin."""

    manager = PluginManager()



    try:

        manager.enable(name)

        success(f"Enabled plugin: {name}")

    except PluginNotFoundError as e:

        error(str(e))

        raise typer.Exit(code=1) from e

    except PluginError as e:

        error(str(e))

        raise typer.Exit(code=1) from e





@plugin_app.command("disable")

def disable_plugin(

    name: str = typer.Argument(..., help="Plugin name to disable"),

) -> None:

    """Disable a plugin without uninstalling."""

    manager = PluginManager()



    try:

        manager.disable(name)

        success(f"Disabled plugin: {name}")

    except PluginNotFoundError as e:

        error(str(e))

        raise typer.Exit(code=1) from e

    except PluginError as e:

        error(str(e))

        raise typer.Exit(code=1) from e





@plugin_app.command("info")

def plugin_info(

    name: str = typer.Argument(..., help="Plugin name"),

) -> None:

    """Show detailed information about a plugin."""

    manager = PluginManager()



    try:

        loaded = manager.get(name)

    except PluginNotFoundError as e:

        error(str(e))

        raise typer.Exit(code=1) from e



    console = get_console()

    manifest = loaded.manifest



    console.print()

    console.print(f"  [bold cyan]{manifest.name}[/bold cyan]  v{manifest.version}")

    console.print(f"  [dim]{manifest.summary}[/dim]")

    console.print()



    if manifest.description:

        console.print(f"  {manifest.description}")

        console.print()



    if manifest.authors:

        console.print(f"  Authors: {', '.join(manifest.authors)}")

    if manifest.license:

        console.print(f"  License: {manifest.license}")

    if manifest.homepage:

        console.print(f"  Homepage: {manifest.homepage}")



    if manifest.entry_points:

        console.print()

        console.print("  [bold]Entry Points:[/bold]")

        for ep in manifest.entry_points:

            console.print(f"    {ep.kind.value}.{ep.name} → {ep.reference}")



    if manifest.permissions:

        console.print()

        console.print("  [bold]Permissions:[/bold]")

        for p in manifest.permissions:

            console.print(f"    {p.value}")



    if manifest.dependencies:

        console.print()

        console.print("  [bold]Dependencies:[/bold]")

        for dep_name, dep_spec in manifest.dependencies.items():

            console.print(f"    {dep_name}: {dep_spec}")



    console.print()





@plugin_app.command("doctor")

def plugin_doctor() -> None:

    """Run health checks on all installed plugins."""

    manager = PluginManager()

    reports = manager.doctor()



    if not reports:

        info("No plugins installed. Nothing to check.")

        return



    console = get_console()

    console.print()

    console.print("  [bold cyan]Plugin Health Report[/bold cyan]")

    console.print()



    ok_count = 0

    for report in reports:

        name = report.plugin_name or "unknown"

        healthy = all(issue.severity != "error" for issue in report.issues)

        if healthy:

            ok_count += 1

            console.print(f"  [green]✓[/green] {name}")

        else:

            console.print(f"  [red]✗[/red] {name}")

            for issue in report.issues:

                severity_color = "red" if issue.severity == "error" else "yellow"

                console.print(f"    [{severity_color}]{issue.severity}[/{severity_color}]: {issue.message}")



    console.print()

    if ok_count == len(reports):

        success(f"All {ok_count} plugins healthy.")

    else:

        console.print(f"  [yellow]{ok_count}/{len(reports)} plugins healthy.[/yellow]")





@plugin_app.command("discover")

def discover_plugins() -> None:

    """List available but not yet installed plugins."""

    manager = PluginManager()

    discovered = manager.discover()



    if not discovered:

        info("No discoverable plugins found.")

        return



    console = get_console()

    console.print()

    console.print("  [bold cyan]Discoverable Plugins[/bold cyan]")

    console.print()



    for plugin in discovered:

        console.print(f"  [bold]{plugin.name}[/bold]  [dim]v{plugin.version}[/dim]  — {plugin.manifest.summary}")



    console.print()

