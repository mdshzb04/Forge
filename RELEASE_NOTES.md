# Forge v1.0.0 Release Notes

## Overview

Forge v1.0.0 is the first production release of the Forge AI optimization runtime. Forge prepares optimized repository-aware context for AI coding assistants, reducing token usage and improving response quality through prompt engineering, output optimization, and intelligent context retrieval.

## What's New

Forge provides a complete developer experience:

```
forge claude          # Launch Claude Code with optimized context
forge codex           # Launch Codex CLI
forge cursor          # Launch Cursor CLI  
forge gemini          # Launch Gemini CLI
forge antigravity     # Launch Antigravity CLI
forge aider           # Launch Aider with context injection
forge opencode        # Launch OpenCode
forge commandcode     # Launch CommandCode

forge start           # Start the background daemon
forge mcp             # Start the MCP server over stdio
forge graph build     # Build a knowledge graph

forge config          # Configure optimization profiles
forge profile         # View/set profiles with rich output
forge status          # Repository and daemon status
forge stats           # Usage statistics
forge doctor          # System diagnostics
forge inspect         # Pipeline and providers
forge explain         # Explain pipeline stages and concepts
```

## Key Capabilities

- **19-stage middleware pipeline** processes every AI request through telemetry, auth, policy, caching, history compression, token planning, context optimization, conversation tracking, Ponytail prompt engineering, Caveman output compression, repository scanning, dependency analysis, symbol extraction, graph enrichment, semantic ranking, streaming, resilience, provider execution, and response optimization.
- **8 AI CLI wrappers** unified through a single runtime path.
- **16 providers** with real HTTP drivers for OpenAI, Anthropic, and Google Gemini.
- **Knowledge graph** integration for intelligent file context injection.
- **Optimization profiles** with 4-5 intensity levels per optimizer.

## Installation

```bash
pip install forgeoptimizer
# or
uv tool install forgeoptimizer
```

## What's Next

- Performance profiling and optimization of 19-stage pipeline under production load
- Standalone binary packaging (PyInstaller/Nuitka)
