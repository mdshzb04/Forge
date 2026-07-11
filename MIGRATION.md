# Migration Guide

## From Pre-1.0 to v1.0.0

Forge v1.0.0 is the first production release. If you were using earlier development versions, the following changes apply:

### CLI Changes

All wrapper commands remain identical:
```bash
forge claude     # unchanged
forge codex      # unchanged
forge cursor     # unchanged
forge antigravity # unchanged
forge gemini     # unchanged
forge aider      # unchanged
```

**New wrappers added**:
```bash
forge opencode    # new
forge commandcode # new
```

**New commands**: `forge stats`, `forge profile`, `forge explain`, `forge inspect`

### Python API

The following internal functions were renamed but backward-compatible aliases exist:

- `build_merged_context(repack_context, restart_root)` — new unified entry point
- `get_merged_context(repo_context)` — still available as deprecated alias
- `build_behavior_instructions()` — still available as deprecated alias

### Configuration

No changes to `forgecli.toml` format. All existing configuration files work without modification.

### Plugin API

The Plugin SDK (`forgecli/sdk/`) is stable. Plugins using `forgecli-plugin.toml` manifests from earlier versions continue to work.

### Provider System

No breaking changes. The same `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GOOGLE_API_KEY` environment variables are used.
