# Forge CLI Command Reference

This document provides a comprehensive guide to all commands available in the `forge` command-line interface.

---

## 1. CLI Wrappers

Forge provides convenience wrappers to prepare optimized context and automatically run your favorite AI coding assistants under a pre-configured environment.

| Command | Target Editor / CLI | Description |
| :--- | :--- | :--- |
| `forge claude` | Claude Code | Launches Claude Code with local MCP server integration and optimized context. |
| `forge cursor` | Cursor CLI | Launches Cursor with global + project-specific MCP registry updates. |
| `forge antigravity` | Antigravity CLI | Launches Antigravity with MCP registration (`~/.gemini/config/mcp_config.json` + CLI/IDE/workspace variants) and optimized context. |
| `forge codex` | Codex CLI | Launches Codex with MCP registration (`~/.codex/config.toml`) and context optimization. |
| `forge aider` | Aider | Launches Aider with the optimized context injected via its `--read` flag (plus `FORGE_CONTEXT` env + project `.mcp.json`). |

### Wrapper Rules & Features
* **Zero-Arguments Block:** To prevent command leakage, direct prompt pass-throughs (e.g., `forge claude "create a file"`) are blocked. Launch the wrappers without positional arguments to open their interactive shell environment.
* **Bypass Cache (`--refresh`):** To bypass cached context and force a fresh optimization compile of the codebase:
  ```bash
  forge claude --refresh
  ```

---

## 2. Configuration Command (`forge config`)

The `config` command allows users to customize their optimization profiles for both the **PromptForge** and **ResponseForge** engines. Settings are persisted automatically in your project's local `forgecli.toml` file.

### View Active Configuration
To view your currently active profiles:
```bash
forge config
```

*Output:*
```
  Forge Configuration
  PromptForge Profile : lite
  ResponseForge Profile  : lite
```

### Toggle Intensities
You can configure both profiles using the `--promptforge` / `-p` and `--responseforge` / `-c` flags:

```bash
# Configure both to "full" mode (Highly recommended for speed and token savings)
forge config --promptforge full --responseforge full

# Configure both to "ultra" mode (Maximum token savings, minimal feedback)
forge config -p ultra -c ultra

# Disable both optimizers
forge config -p off -c off
```

### Available Intensities
* **`off`**: Disables the optimizer.
* **`lite`** (Default): Standard, balanced optimization rules.
* **`full`**: Strict YAGNI (PromptForge) and concise fragment-only messaging (ResponseForge).
* **`ultra`**: Aggressive context pruning and extreme brevity.

---

## 3. Core MCP Runtime (`forge mcp`)

Starts the Model Context Protocol (MCP) server over standard input/output (stdio).

```bash
forge mcp
```

### Purpose
Used internally by editor integrations (like Cursor and Claude Code) to interactively fetch tools, query codebase graphs, lookup file structures, and perform semantic indexing.

---

## 4. Background Daemon (`forge start`)

Launches the long-running context runtime daemon to watch your project folder and prepare index updates in the background.

```bash
forge start [--port 16868]
```

### Options
* `--port`, `-p`: Specifies the port to run the daemon HTTP server on (default is `16868`).

---

## 5. Knowledge Graph builder (`forge graph build`)

Builds a complete repository knowledge graph.

```bash
forge graph build
```

### Purpose
Scans all import paths, structures, and functions in your repository to build a global semantic symbol index. This is used by the search algorithms in the MCP server to answer complex codebase questions.
