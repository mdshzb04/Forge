# Forge

<p align="center">
  <a href="https://github.com/mdshzb04/Forge/actions/workflows/ci.yml">
    <img src="https://github.com/mdshzb04/Forge/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://pypi.org/project/forgectx/">
    <img src="https://img.shields.io/pypi/v/forgectx.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/forgectx/">
    <img src="https://img.shields.io/pypi/pyversions/forgectx.svg" alt="Supported Python Versions">
  </a>
  <a href="https://github.com/mdshzb04/Forge/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/mdshzb04/Forge.svg" alt="License: MIT">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code Style: Ruff">
  </a>
</p>

Forge is a pre-launch context preparation tool for AI coding assistants. Before you run `claude`, `codex`, or `cursor`, Forge scans your repository, extracts symbols and dependencies, builds a structured summary, injects configurable behavior instructions, and passes the optimized context to the AI tool through environment variables and MCP tools.

## Core Philosophy

> [!IMPORTANT]
> **Forge optimizes what it controls.**
>
> Forge focuses on three areas:
>
> - **Repository Intelligence** — Symbol extraction, dependency analysis, file scanning, and native graph generation.
> - **Behavior Optimization** — Configurable implementation guidance (Ponytail YAGNI rules) and response style optimization (Caveman conciseness rules).
> - **Runtime Infrastructure** — Zero-configuration wrappers, context caching, background daemon, and MCP server.
>
> Forge prepares context before the AI session begins. It does **not** modify provider billing, quota accounting, model pricing, model inference, or the AI client's internal tool selection logic.

## Architecture

Forge has a single unified context preparation path used by all wrappers:

1. **Repository scan** — Extracts files, symbols (classes/functions), and dependencies (imports/requires) using parallel regex-based parsers for Python, JS, TS, JSX, and TSX.
2. **Semantic ranking** — Ranks files by TF-IDF query relevance with dependency centrality scoring.
3. **AST pruning** — Uses tree-sitter to prune files to only relevant symbols, keeping context lean.
4. **Behavior injection** — Prepends intensity-gated Ponytail (YAGNI) and Caveman (conciseness) instructions.
5. **Compression** — Collapses whitespace, strips boilerplate, and removes redundant content.
6. **Caching** — Fingerprints repositories and caches context between launches.
7. **Launch** — Sets `FORGE_CONTEXT` env var and starts the AI CLI.

### Native Graph Builder

Forge includes a native Python graph builder (`forgecli/graph/native_builder.py`) that generates `forgegraph-out/graph.json` without external binaries. When the external `graphify` binary is available, it takes priority for advanced features (Leiden clustering, LLM-powered analysis). The native builder always works as a fallback.

## Installation

```bash
uv tool install forgectx
```

The CLI entrypoint is `forge`.

---

## Interfaces

Forge provides two ways to connect with your AI coding tools:

1. **Convenience Wrappers** (`forge claude`, `forge cursor`, `forge codex`, `forge antigravity`, `forge gemini`) — Automatically prepare context, configure MCP, and launch the target AI CLI.
2. **MCP Server** (`forge mcp`) — Standard stdio JSON-RPC interface exposing 6 tools that AI clients can call during sessions.

---

## Command Reference

| Command | Description |
| -------- | ----------- |
| `forge claude` | Launch Claude Code with optimized context |
| `forge codex` | Launch Codex CLI with optimized context |
| `forge cursor` | Launch Cursor CLI with optimized context |
| `forge antigravity` | Launch Antigravity CLI with optimized context |
| `forge gemini` | Launch Gemini CLI with optimized context |
| `forge mcp` | Start the stdio MCP server |
| `forge start` | Start the background daemon |
| `forge graph build` | Build a codebase graph (native or external) |
| `forge config` | Configure optimization profiles |
| `forge status` | Show repository, daemon, and optimization status |
| `forge doctor` | Verify installation and dependencies |
| `forge inspect` | Display active pipeline and optimization stages |
| `forge stats` | Show cache metrics and pipeline performance |
| `forge profile` | View or set optimization profiles |
| `forge explain` | Explain pipeline stages, concepts, or topics |
| `forge plugin list` | List installed plugins |
| `forge --version` | Show version |

Use `--refresh` to bypass the cache on any wrapper command:
```bash
forge claude --refresh
```

---

## MCP Tools

Forge exposes 6 tools over MCP:

* `get_optimized_context` — Full optimized repository context with optional query filtering
* `get_summary` — Repository layout, file count, and size summary
* `get_dependency_graph` — Module/file import relationships
* `file_lookup` — File contents by relative path
* `symbol_lookup` — Class/function definitions and locations
* `semantic_search` — Keyword search across codebase chunks

> [!IMPORTANT]
> Forge exposes these tools, but whether they are called depends on the AI client's internal orchestration. Forge does not control tool selection.

---

## Environment Variables

| Variable | Purpose |
| -------- | -------- |
| `FORGE_CONTEXT` | Optimized pre-launch context text |
| `FORGE_CONTEXT_FILE` | Path to the cached context file |
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
