# Sample ForgeCLI Plugin

This directory contains a minimal example ForgeCLI plugin demonstrating the plugin SDK.

## Structure

```
sample-plugin/
├── forgecli-plugin.toml   # Plugin manifest (required)
├── sample_plugin.py        # Plugin implementation
└── README.md               # This file
```

## Entry Points

This plugin registers three extension points:

1. **AI Provider** (`provider.sample`) — A deterministic test provider that returns sample responses.
2. **Repository Analyzer** (`repository-analyzer.sample`) — Logs Python file counts in the repository.
3. **Context Optimizer** (`context-optimizer.sample`) — Strips TODO/FIXME comment lines from context.

## Installing

```bash
# Install from local directory
forge plugin install examples/sample-plugin

# Enable it
forge plugin enable sample-plugin

# Verify
forge plugin info sample-plugin
forge plugin doctor
```

## Uninstalling

```bash
forge plugin disable sample-plugin
forge plugin remove sample-plugin
```
