"""TOML writer helper to update ForgeCLI config settings on the fly."""



from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

try:

    import tomllib

except ModuleNotFoundError:  # pragma: no cover

    import tomli as tomllib  # type: ignore[no-redef,import-not-found]





def dump_toml(data: dict[str, Any]) -> str:

    """Serialize a dictionary to a basic TOML string (handles flat tables and primitive values)."""

    lines = []



    for k, v in sorted(data.items()):

        if not isinstance(v, dict):

            if isinstance(v, bool):

                lines.append(f"{k} = {str(v).lower()}")

            elif isinstance(v, (int, float)):

                lines.append(f"{k} = {v}")

            elif isinstance(v, str):

                lines.append(f'{k} = "{v}"')

            elif isinstance(v, list):

                items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)

                lines.append(f"{k} = [{items}]")





    for section_name, section_val in sorted(data.items()):

        if isinstance(section_val, dict):

            lines.append(f"\n[{section_name}]")

            for k, v in sorted(section_val.items()):

                if isinstance(v, bool):

                    lines.append(f"{k} = {str(v).lower()}")

                elif isinstance(v, (int, float)):

                    lines.append(f"{k} = {v}")

                elif isinstance(v, str):

                    lines.append(f'{k} = "{v}"')

                elif isinstance(v, list):

                    items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)

                    lines.append(f"{k} = [{items}]")



    return "\n".join(lines).strip() + "\n"





def update_config(

    default_provider: str | None = None,

    default_model: str | None = None,

    clear_provider: bool = False,

    clear_model: bool = False,

    promptforge: str | None = None,

    responseforge: str | None = None,

    output_optimization: str | None = None,

    loop_engineering_pattern: str | None = None,

    claude_usd_limit: float | None = None,

    cursor_usd_limit: float | None = None,

    codex_usd_limit: float | None = None,

    antigravity_usd_limit: float | None = None,

    loop_engineering_enabled: bool | None = None,

) -> Path:

    """Update defaults in the active forgecli.toml configuration file."""

    from forgecli.config.loader import ConfigLoader



    loader = ConfigLoader()



    candidates = loader._candidate_paths()

    target_path = None

    for p in candidates:

        if p.exists() and p.name != "pyproject.toml":

            target_path = p

            break



    if not target_path:

        target_path = Path("./forgecli.toml")



    data: dict[str, Any] = {}

    if target_path.exists():

        with contextlib.suppress(Exception):

            data = tomllib.loads(target_path.read_text(encoding="utf-8"))



    if "providers" not in data:

        data["providers"] = {}



    if clear_provider:

        data["providers"].pop("default", None)

    elif default_provider is not None:

        data["providers"]["default"] = default_provider



    if clear_model:

        data["providers"].pop("default_model", None)

    elif default_model is not None:

        data["providers"]["default_model"] = default_model



    if promptforge is not None:

        if "prompt_optimizer" not in data:

            data["prompt_optimizer"] = {}

        data["prompt_optimizer"]["intensity"] = promptforge

        data["prompt_optimizer"]["enabled"] = promptforge != "off"



    if responseforge is not None:

        if "responseforge" not in data:

            data["responseforge"] = {}

        data["responseforge"]["intensity"] = responseforge

        data["responseforge"]["enabled"] = responseforge != "off"



    if output_optimization is not None:

        if "output_optimization" not in data:

            data["output_optimization"] = {}

        data["output_optimization"]["intensity"] = output_optimization

        data["output_optimization"]["enabled"] = output_optimization != "off"



    if any(

        value is not None

        for value in (

            loop_engineering_pattern,

            claude_usd_limit,

            cursor_usd_limit,

            codex_usd_limit,

            antigravity_usd_limit,

            loop_engineering_enabled,

        )

    ):

        if "loop_engineering" not in data:

            data["loop_engineering"] = {}

        if loop_engineering_pattern is not None:

            data["loop_engineering"]["pattern"] = loop_engineering_pattern

        if claude_usd_limit is not None:

            data["loop_engineering"]["claude_usd_limit"] = claude_usd_limit

        if cursor_usd_limit is not None:

            data["loop_engineering"]["cursor_usd_limit"] = cursor_usd_limit

        if codex_usd_limit is not None:

            data["loop_engineering"]["codex_usd_limit"] = codex_usd_limit

        if antigravity_usd_limit is not None:

            data["loop_engineering"]["antigravity_usd_limit"] = antigravity_usd_limit

        if loop_engineering_enabled is not None:

            data["loop_engineering"]["enabled"] = loop_engineering_enabled



    content = dump_toml(data)

    target_path.write_text(content, encoding="utf-8")

    loader.invalidate()

    return target_path

