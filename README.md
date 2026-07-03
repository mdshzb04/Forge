# Forge

> AI optimization runtime for modern software development.

Forge improves AI-assisted development by helping AI systems understand your codebase more effectively. It automatically converts repositories into a searchable knowledge graph, optimizes prompts before they're processed, reduces unnecessary token usage, and caches reusable context for faster, more efficient AI workflows.

## Features

- Converts your codebase into a searchable knowledge graph
- Automatic project detection
- Prompt optimization
- Token optimization
- Intelligent caching
- Fast local execution
- Zero configuration
- Cross-platform support (Windows, macOS, and Linux)

## Installation

```bash
uv tool install forge
```

## Getting Started

Open any project and build its knowledge graph.

```bash
forge graph build
```

Forge automatically analyzes your project, builds or updates its knowledge graph, optimizes context before it reaches your AI model, reduces unnecessary tokens, and reuses cached information to improve speed and efficiency.

No initialization or manual setup is required.

## How It Works

Forge combines three core capabilities to improve AI-assisted development:

- Converts your codebase into a structured knowledge graph for better repository understanding.
- Optimizes prompts before they reach your AI model.
- Reduces unnecessary tokens to improve efficiency, lower cost, and reduce latency.

These optimizations happen automatically with no additional configuration.

## Platform Support

- Linux
- macOS
- Windows

## Development

```bash
git clone <repository-url>
cd Forge

pip install -e .
```

Run the test suite:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

## License

MIT
---


<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/03f3c2e2-424c-4784-8a59-b2b0f4b99447" />





<img width="1854" height="1005" alt="image" src="https://github.com/user-attachments/assets/6eb06d10-6f1f-4648-b679-028368362c24" />





## License

[MIT](LICENSE)
