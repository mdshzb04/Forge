"""Single source of truth for the terminal AI agents Forge supports.

Each :class:`AgentSpec` describes how to launch an agent CLI and where to
register the Forge MCP server so the agent receives optimized context. Adding
a new agent is a single entry here — the wrapper command, help text, and MCP
auto-configuration are all driven off this registry.
"""



from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)

class MCPTarget:

    """A location + format where the Forge MCP server should be registered.

    ``base`` selects the anchor directory: ``"home"`` for a per-user config
    (e.g. ``~/.codex/config.toml``) or ``"repo"`` for a project-local file
    (e.g. ``<repo>/.cursor/mcp.json``). ``relpath`` is joined onto that anchor.
    """



    base: str

    relpath: str

    fmt: str = "json"

    table: str = "mcpServers"

    label: str = ""





@dataclass(frozen=True)

class AgentSpec:

    """A terminal AI agent Forge can prepare context for and launch."""



    id: str

    name: str

    binary: str

    install_hint: str

    mcp_targets: tuple[MCPTarget, ...] = field(default_factory=tuple)

    supports_mcp: bool = True

    context_flag: str | None = None

    """CLI flag used to inject the optimized context file at launch.

    For agents without native MCP (e.g. Aider's ``--read``), Forge passes the
    merged context file as ``<context_flag> <file>`` so the agent still ingests
    the optimized context. ``None`` means the agent receives context via MCP.
    """





AGENTS: dict[str, AgentSpec] = {

    "claude": AgentSpec(

        id="claude",

        name="Claude Code",

        binary="claude",

        install_hint="Install Claude Code: https://docs.anthropic.com/en/docs/claude-code",

        mcp_targets=(

            MCPTarget(base="home", relpath=".claude.json", fmt="json", label="Claude Code"),

        ),

    ),

    "codex": AgentSpec(

        id="codex",

        name="Codex CLI",

        binary="codex",

        install_hint="Install OpenAI Codex CLI: https://developers.openai.com/codex/cli/",

        mcp_targets=(

            MCPTarget(

                base="home",

                relpath=".codex/config.toml",

                fmt="toml",

                table="mcp_servers",

                label="Codex CLI",

            ),

        ),

    ),

    "cursor": AgentSpec(

        id="cursor",

        name="Cursor CLI",

        binary="cursor",

        install_hint="Install Cursor CLI: https://cursor.com/docs/cli/overview",

        mcp_targets=(

            MCPTarget(base="home", relpath=".cursor/mcp.json", fmt="json", label="Cursor (global)"),

            MCPTarget(

                base="repo", relpath=".cursor/mcp.json", fmt="json", label="Cursor (project)"

            ),

        ),

    ),

    "antigravity": AgentSpec(

        id="antigravity",

        name="Antigravity CLI",

        binary="antigravity",

        install_hint="Install Antigravity CLI",







        mcp_targets=(

            MCPTarget(

                base="home",

                relpath=".gemini/config/mcp_config.json",

                fmt="json",

                label="Antigravity (unified)",

            ),

            MCPTarget(

                base="home",

                relpath=".gemini/antigravity-cli/mcp_config.json",

                fmt="json",

                label="Antigravity CLI",

            ),

            MCPTarget(

                base="home",

                relpath=".gemini/antigravity/mcp_config.json",

                fmt="json",

                label="Antigravity IDE",

            ),

            MCPTarget(

                base="repo",

                relpath=".agents/mcp_config.json",

                fmt="json",

                label="Antigravity (workspace)",

            ),

        ),

    ),

    "gemini": AgentSpec(

        id="gemini",

        name="Gemini CLI",

        binary="gemini",

        install_hint="Install Gemini CLI",

        mcp_targets=(

            MCPTarget(

                base="home",

                relpath=".gemini/config/mcp_config.json",

                fmt="json",

                label="Gemini (unified)",

            ),

            MCPTarget(

                base="home",

                relpath=".gemini/gemini-cli/mcp_config.json",

                fmt="json",

                label="Gemini CLI",

            ),

            MCPTarget(

                base="repo",

                relpath=".agents/mcp_config.json",

                fmt="json",

                label="Gemini (workspace)",

            ),

        ),

    ),

    }
