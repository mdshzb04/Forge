# Changelog

## 1.0.0 (2024-07-09)

### Forge v1.0 — Initial Production Release

Forge is a lightweight, high-performance AI optimization runtime that prepares repository-aware context before launching supported AI coding tools.

### Features

- **8 AI CLI Wrappers**: Unified launch for Claude Code, Codex CLI, Cursor CLI, Antigravity, Gemini CLI, Aider, OpenCode, and CommandCode through a single `launch_wrapper()` path.
- **19-Stage Middleware Pipeline**: Telemetry → Auth → Policy → Cache → History → Token → Context → Conversation → ResponseForge → PromptForge → Repository → DepGraph → SymbolLookup → ForgeGraph → SemanticRetrieval → Streaming → Resilience → Provider → ResponseOptimizer.
- **Optimization Profiles**: PromptForge (prompt YAGNI rules), ResponseForge (output conciseness), and Output Optimization with `off/lite/full/ultra/wenyan` intensities.
- **ForgeGraph Integration**: Knowledge graph generation for intelligent context retrieval with `forge graph build`.
- **MCP Server**: Stdio Model Context Protocol server with 6 tools (`get_optimized_context`, `get_summary`, `get_dependency_graph`, `file_lookup`, `symbol_lookup`, `semantic_search`).
- **Background Daemon**: Repository watcher with auto-refresh, chunking, and graph snapshot on port 16868.
- **16 Provider Drivers**: OpenAI, Anthropic, Google Gemini, OpenRouter, Groq, Mistral, DeepSeek, GLM, Qwen, Kimi, Ollama, LM Studio, and more — with real HTTP implementations for the big three.
- **Developer Diagnostics**: `forge inspect`, `forge stats`, `forge doctor`, `forge profile`, `forge explain`.
- **Configuration**: TOML-based `forgecli.toml` with environment variable override for all settings.
- **Packaging**: pip install, CI/CD across ubuntu/macos/windows, PyPI ready.

### System

- Python 3.12+ required
- 463+ tests passing
- 40% faster startup vs initial implementation (0.63s CLI import)
- MIT License
