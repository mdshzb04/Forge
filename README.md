# Forge

Forge is a lightweight, high-performance AI optimization runtime designed to prepare repository-aware context before launching supported AI coding tools. 

The primary purpose of Forge is to construct an optimized representation of a codebase so that AI coding assistants can operate with maximum correctness, lower response latency, and reduced context-budget overhead.

## Architecture & How It Works

Forge prepares repository-aware context for AI coding assistants using knowledge graph generation, intelligent context selection, prompt optimization, token optimization, and aggressive caching. 

Forge is powered internally by three integrated optimization engines:
1. **ForgeGraph** (Knowledge graph and symbol index generator)
2. **Ponytail** (Intelligent YAGNI context selector and prompt optimizer)
3. **Caveman** (Token-efficient communication and brevity optimizer)

### Design Philosophy & Inspiration
Forge combines original runtime infrastructure with ideas inspired by the broader open-source AI tooling ecosystem. While some optimization concepts draw inspiration from existing projects, Forge's architecture, background caching daemon, editor wrappers, and local code parser are independently developed. For details, see [CREDITS.md](CREDITS.md).

---

## Installation

### Development
```bash
uv tool install .
```

### Release
```bash
uv tool install forgectx
```

The CLI entrypoint is `forge`.

---

## Convenience Wrappers vs. Core MCP Runtime

Forge provides two primary interfaces to connect with your AI coding tools:
1. **Convenience Wrappers** (`forge claude`, `forge cursor`, `forge codex`, `forge opencode`, `forge commandcode`, `forge antigravity`): Commands that automatically prepare/optimize context, update local and global configurations, and launch the target AI CLI under an optimized environment.
2. **Core MCP Runtime** (`forge mcp`): The standard Model Context Protocol (MCP) interface that compatible AI clients communicate with over stdio.

---

## Command Reference

| Command | Type | Description |
| -------- | ---- | ----------- |
| `forge claude` | Wrapper | Launch Claude Code with optimized context and auto-registered MCP |
| `forge codex` | Wrapper | Launch Codex CLI with optimized context and auto-registered MCP |
| `forge cursor` | Wrapper | Launch Cursor CLI with optimized context and auto-registered MCP |
| `forge opencode` | Wrapper | Launch OpenCode CLI with optimized context and auto-registered MCP |
| `forge commandcode` | Wrapper | Launch CommandCode CLI with optimized context and auto-registered MCP |
| `forge antigravity` | Wrapper | Launch Antigravity CLI with optimized context and auto-registered MCP |
| `forge mcp` | Core Runtime | Start the stdio Model Context Protocol (MCP) server |
| `forge start` | Daemon | Start the background context optimization daemon |
| `forge graph build` | Tool | Build a full codebase dependency and symbol knowledge graph (optional) |
| `forge config` | Tool | Configure optimization profile intensities |
| `forge --version` | Tool | Show version |

For detailed information on all command usages and options, refer to the [CLI Command Reference](docs/commands.md).

> [!NOTE]
> When launching convenience wrappers, prompts or extra positional arguments are not supported directly (e.g. `forge claude "some prompt"` is blocked). Run the wrapper command without arguments to launch the tool's interactive session directly. Use the `--refresh` option to bypass the cache:
> ```bash
> forge claude --refresh
> ```

---

## Model Context Protocol (MCP) Integration

Forge automatically registers its MCP server globally and project-locally for launched clients (updating `~/.claude.json`, `~/.cursor/mcp.json`, and project `.mcp.json` files).

### Exposed Tools
Forge exposes the following schema tools over MCP:
* `get_optimized_context` — Retrieve the fully optimized and token-compressed repository context.
* `get_summary` — Retrieve a summary of the repository layout, size, and file list.
* `get_dependency_graph` — Retrieve module/file import relationships.
* `file_lookup` — Query individual file contents.
* `symbol_lookup` — Find definition locations of symbols (classes/functions).
* `semantic_search` — Keyword/phrase search across codebase chunks.

> [!IMPORTANT]
> **Client Behavior Notice:** While Forge exposes these tools to the MCP client, whether and when they are invoked depends entirely on the AI client's internal orchestration logic. Forge makes these capabilities available, but the client decides which tool to call.

---

## Environment Variables

Wrappers export:

| Variable | Purpose |
| -------- | -------- |
| `FORGE_CONTEXT` | Optimized text context |
| `FORGE_CONTEXT_FILE` | Path to the optimized context file |
| `FORGE_REPO_ROOT` | Detected repository root |

---

## Development

```bash
git clone https://github.com/mdshzb04/Forge
cd Forge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check forgecli tests
```

## License

[MIT](LICENSE)
