"""Wrapper commands: forge claude | codex | cursor | antigravity | aider.

A single factory builds the per-agent Typer callback from the agent registry,
so adding an agent in :mod:`forgecli.runtime.agents` is all that's required.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from forgecli.runtime.agents import AGENTS
from forgecli.runtime.wrappers import launch_wrapper

_WRAPPER_SETTINGS = {
    "allow_extra_args": True,
    "allow_interspersed_args": True,
    "ignore_unknown_options": True,
}


def make_agent_cmd(agent_id: str) -> Callable[..., None]:
    """Build a Typer callback that launches ``agent_id`` with Forge optimization."""
    name = AGENTS[agent_id].name

    def _cmd(
        ctx: typer.Context,
        path: str = typer.Option(".", "--path", "-p", help="Project root."),
        refresh: bool = typer.Option(False, "--refresh", help="Bypass cached Forge context."),
    ) -> None:
        launch_wrapper(agent_id, list(ctx.args), path=Path(path), force_prepare=refresh)

    _cmd.__doc__ = f"Launch {name} with Forge prompt + token optimization."
    _cmd.__name__ = f"{agent_id}_cmd"
    return _cmd


__all__ = ["_WRAPPER_SETTINGS", "make_agent_cmd"]
