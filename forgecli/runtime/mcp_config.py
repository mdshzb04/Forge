"""Automated registration of the Forge MCP server for terminal AI agents.

Registration is driven entirely by the agent registry in
:mod:`forgecli.runtime.agents`. Each agent declares one or more
:class:`~forgecli.runtime.agents.MCPTarget` locations; this module writes the
``forge`` MCP entry into each, handling both JSON and TOML config formats.
Writes are idempotent and best-effort — a failure for one agent never blocks a
launch, it just falls back to the FORGE_CONTEXT env vars + project ``.mcp.json``.
"""



from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from forgecli.cli.ui import info, success
from forgecli.runtime.agents import AGENTS, AgentSpec, MCPTarget


def get_forge_mcp_entry() -> dict[str, Any]:

    """Resolve the absolute path to 'forge' to ensure robust launching in IDEs."""

    import shutil
    import sys





    forge_bin = shutil.which("forge")

    if forge_bin:

        return {"command": str(Path(forge_bin).resolve()), "args": ["mcp"]}





    python_bin = sys.executable

    if python_bin:

        return {"command": python_bin, "args": ["-m", "forgecli.cli.main", "mcp"]}





    return {"command": "forge", "args": ["mcp"]}





def configure_mcp_for_all(repo_root: Path) -> None:

    """Register the Forge MCP server for every supported agent + project-local."""

    for spec in AGENTS.values():

        configure_mcp_for_agent(spec, repo_root)

    configure_project_local_mcp(repo_root)





def configure_mcp_for_agent(spec: AgentSpec, repo_root: Path) -> None:

    """Write the Forge MCP entry into every target declared by ``spec``."""

    if not spec.supports_mcp:

        return

    for target in spec.mcp_targets:

        path = _resolve_target_path(target, repo_root)

        try:

            if target.fmt == "toml":

                _write_toml_mcp(path, target.table)

            else:

                _write_json_mcp(path, target.table)

        except Exception as e:

            info(f"Note: Could not auto-configure {target.label or spec.name} MCP: {e}")





def _resolve_target_path(target: MCPTarget, repo_root: Path) -> Path:

    anchor = Path.home() if target.base == "home" else repo_root

    return anchor / target.relpath





def _write_json_mcp(path: Path, table: str) -> None:

    """Idempotently add the ``forge`` server to a JSON config at ``path``."""

    path.parent.mkdir(parents=True, exist_ok=True)



    data: dict = {}

    if path.exists():

        content = path.read_text(encoding="utf-8").strip()

        if content:

            try:

                data = json.loads(content)

            except json.JSONDecodeError:

                info(f"Could not parse {path} as valid JSON. Skipping auto-config.")

                return



    servers = data.get(table)

    if not isinstance(servers, dict):

        servers = {}

        data[table] = servers



    entry = get_forge_mcp_entry()





    current = servers.get("forge")

    if not current or current.get("command") == "forge" or current != entry:

        servers["forge"] = entry

        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        success(f"✨ Configured Forge MCP server in {path}.")





def _write_toml_mcp(path: Path, table: str) -> None:

    """Idempotently add the ``forge`` server to a TOML config at ``path``.

    Parses the existing TOML, removes any existing [<table>.forge] section and
    any stale bare command/args keys from previous writers, then appends a clean
    [<table>.forge] block.
    """

    import re



    path.parent.mkdir(parents=True, exist_ok=True)



    entry = get_forge_mcp_entry()

    if path.exists():

        existing = path.read_text(encoding="utf-8")

        with contextlib.suppress(Exception):

            import tomllib



            parsed = tomllib.loads(existing)

            servers = parsed.get(table)

            if isinstance(servers, dict) and "forge" in servers:

                current = servers["forge"]

                if current.get("command") != "forge" and current == entry:

                    return





        section_pat = re.compile(

            rf"^\s*\[{re.escape(table)}\.forge\].*?(?=(?:^\s*\[)|\Z)",

            re.MULTILINE | re.DOTALL,

        )

        cleaned = section_pat.sub("", existing)

    else:

        cleaned = ""









    lines: list[str] = []

    in_section = bool(cleaned.strip().startswith("[") if cleaned else False)

    for raw_line in cleaned.splitlines():

        stripped = raw_line.strip()

        if stripped.startswith("["):

            in_section = True

            lines.append(raw_line)

        elif stripped == "":

            lines.append(raw_line)

            in_section = False

        elif in_section:

            lines.append(raw_line)

        elif stripped.startswith("command =") or stripped.startswith("args ="):

            continue

        elif stripped.startswith("model") or stripped.startswith("preferred"):

            lines.append(raw_line)

        else:

            lines.append(raw_line)



    cleaned = "\n".join(lines)

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()



    args_str = ", ".join(f'"{a}"' for a in entry["args"])

    block = f'\n[{table}.forge]\ncommand = "{entry["command"]}"\nargs = [{args_str}]\n'



    prefix = cleaned + "\n" if cleaned else ""

    path.write_text(prefix + block, encoding="utf-8")

    success(f"✨ Configured Forge MCP server in {path}.")





def configure_project_local_mcp(repo_root: Path) -> None:

    """Create a project-local .mcp.json for tools that support auto-discovery."""

    _write_json_mcp(repo_root / ".mcp.json", "mcpServers")





__all__ = [

    "configure_mcp_for_agent",

    "configure_mcp_for_all",

    "configure_project_local_mcp",

]

