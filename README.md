# Forge

Forge is an AI optimization runtime. It prepares your repository context at light speed — prompt optimization and token compression — then launches the AI CLI you already use.

Install:

```bash
uv tool install forgectx
```

The command is `forge`.

## What it does

When you run `forge claude`, `forge codex`, `forge cursor`, `forge opencode`, or `forge commandcode`, Forge:

1. Detects your git repository (or current directory)
2. Builds a **shallow** repo snapshot — it does **not** index your whole codebase
3. Runs prompt optimization (Ponytail ruleset) and token compression
4. Reuses cached results when nothing important changed
5. Launches the selected CLI with `FORGE_CONTEXT` and `FORGE_CONTEXT_FILE` set

Wrappers feel instant because Forge skips full graph builds during normal use.

## Commands

| Command | Description |
| -------- | ------------ |
| `forge claude` | Launch Claude Code with optimized context |
| `forge codex` | Launch Codex CLI with optimized context |
| `forge cursor` | Launch Cursor CLI with optimized context |
| `forge opencode` | Launch OpenCode CLI with optimized context |
| `forge commandcode` | Launch CommandCode CLI with optimized context |
| `forge graph build` | Optionally build a full knowledge graph via Graphify |
| `forge --version` | Show version |

Pass through any flags your CLI supports:

```bash
forge claude -- "fix the failing test in tests/test_foo.py"
forge codex --help
forge cursor --refresh
```

Use `--refresh` to bypass Forge's context cache.



If you want a full codebase knowledge graph :

```bash
uv tool install graphifyy
forge graph build
```



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
git tag v1.0.0
git push origin v1.0.0
```

Publish jobs run **only on `v*` tags**. On regular pushes to `main`, those jobs show as **Skipped** — that is expected, not a failure.

Configure GitHub environments `testpypi` and `pypi` with PyPI trusted publishing for package name `forgectx`.

---

<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/03f3c2e2-424c-4784-8a59-b2b0f4b99447" />

<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/6eb06d10-6f1f-4648-b679-028368362c24" />

## License

[MIT](LICENSE)
