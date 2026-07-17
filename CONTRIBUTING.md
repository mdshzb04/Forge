# Contributing to Forge

Thank you for your interest in contributing to **Forge**! Forge is a lightweight, high-performance AI optimization runtime designed to prepare repository-aware context before launching supported AI coding tools.

This document outlines the guidelines and best practices for contributing to the codebase.

---

## Code of Conduct

We expect all contributors to adhere to standard respectful community interactions. Be kind, helpful, and professional in all communications.

---

## Getting Started

### Prerequisites
- **Python 3.12** or higher.
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip` + `venv`.

### Local Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/mdshzb04/Forge.git
   cd Forge
   ```

2. **Create and Activate a Virtual Environment**
   Using `uv` (recommended):
   ```bash
   uv venv
   source .venv/bin/activate
   ```
   Or using standard Python:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   Install Forge in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

---

## Development Workflow

### Running Tests

We use `pytest` for all unit and integration testing. Ensure your tests pass before submitting any pull requests.

To run the full test suite:
```bash
pytest
```

To run a specific test file:
```bash
pytest tests/test_mcp_config.py
```

### Code Quality & Styling

We use **Ruff** for linting, formatting, and import sorting.

To check for style violations:
```bash
ruff check forgecli tests
```

To automatically fix violations and format code:
```bash
ruff check --fix forgecli tests
ruff format forgecli tests
```

### Static Type Checking

We use **mypy** for static type verification:
```bash
mypy forgecli
```

---

## Code Architecture

Forge consists of two main pillars:
1. **`forgecli.runtime`**: Orchestrates runtime environments, command wrappers, daemon processing, and MCP standard input/output configurations.
2. **`forgecli.optimizer`**: Contains token compression, PromptForge (YAGNI pruning rules), and ResponseForge (brevity prompts) components.

Ensure any changes respect this separation of concerns.

---

## Pull Request Guidelines

1. **Branch Naming**: Use descriptive branch names (e.g., `feature/optimize-caching`, `bugfix/fix-toml-regex`).
2. **Commit Messages**: Write clear, descriptive commit messages in the imperative mood (e.g., `Fix TOML config regex to correctly match blocks`).
3. **Add Tests**: If you are adding a new feature or fixing a bug, please write corresponding tests in the `tests/` directory.
4. **Documentation**: Update the `README.md`, `docs/`, or docstrings if your changes modify any public-facing behaviors or flags.
5. **CI Compliance**: Ensure the Github Actions CI build passes.

Thank you for making Forge better for everyone! 🚀
