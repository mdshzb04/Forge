# Forge

Forge is an AI optimization runtime. It prepares your repository context at light speed — prompt optimization and token compression — then launches the AI CLI you already use.

Install:

**Development:**
```bash
uv tool install .
```

**Release:**
```bash
uv tool install forgectx
```

The command is `forge`.

## Convenience Wrappers vs. Core MCP Runtime

Forge provides two primary interfaces to connect with your AI coding tools:
1. **Convenience Wrappers** (`forge claude`, `forge cursor`, etc.): Commands that automatically prepare/optimize context, update local and global configurations, and launch the target AI CLI under an optimized environment.
2. **Core MCP Runtime** (`forge mcp`): The standard Model Context Protocol (MCP) interface that compatible AI clients communicate with over stdio.

## Commands

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
| `forge graph build` | Tool | Build a full knowledge graph via Graphify (optional) |
| `forge --version` | Tool | Show version |

> [!NOTE]
> When launching convenience wrappers, prompts or extra positional arguments are not supported directly (e.g. `forge claude "some prompt"` is blocked). Run the wrapper command without arguments to launch the tool's interactive session directly. Use the `--refresh` option to bypass the cache:
> ```bash
> forge claude --refresh
> ```

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



## Environment variables

Wrappers export:

| Variable | Purpose |
| -------- | -------- |
| `FORGE_CONTEXT` | Optimized text context |
| `FORGE_CONTEXT_FILE` | Path to the optimized context file |
| `FORGE_REPO_ROOT` | Detected repository root |

## Development

```bash
git clone https://github.com/mdshzb04/Forge
cd Forge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check forgecli tests
```

## Release

Push a version tag to publish to TestPyPI and PyPI:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Publish jobs run **only on `v*` tags**. On regular pushes to `main`, those jobs show as **Skipped** — that is expected, not a failure.

Configure GitHub environments `testpypi` and `pypi` with PyPI trusted publishing for package name `forgectx`.

---

<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/03f3c2e2-424c-4784-8a59-b2b0f4b99447" />

<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/6eb06d10-6f1f-4648-b679-028368362c24" />

## License

[MIT](LICENSE)
