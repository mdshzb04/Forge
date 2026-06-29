"""Helpers to grab git diffs without importing the graphify package."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class GitRepoError(RuntimeError):
    """Raised when a git operation fails."""


def is_git_repo(root: Path) -> bool:
    """Return True if ``root`` is inside a git working tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitRepoError("git executable not found on PATH") from exc
    return result.returncode == 0 and result.stdout.strip() == "true"


def run_git(args: list[str], root: Path) -> str:
    """Run ``git <args>`` in ``root`` and return stdout (raises on failure)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitRepoError("git executable not found on PATH") from exc
    if result.returncode != 0:
        raise GitRepoError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout


def diff_staged(root: Path) -> str:
    """Return the staged diff (``git diff --cached``) for ``root``."""
    if not is_git_repo(root):
        return ""
    return run_git(["diff", "--cached", "--binary"], root)


def diff_unstaged(root: Path) -> str:
    """Return the unstaged working-tree diff (``git diff``) for ``root``."""
    if not is_git_repo(root):
        return ""
    return run_git(["diff", "--binary"], root)


def diff_between(root: Path, base: str, head: str = "HEAD") -> str:
    """Return ``git diff <base>..<head>`` for ``root``."""
    return run_git(["diff", "--binary", f"{base}..{head}"], root)


def status_porcelain(root: Path) -> list[str]:
    """Return the output of ``git status --porcelain`` (one line per entry)."""
    if not is_git_repo(root):
        return []
    out = run_git(["status", "--porcelain"], root)
    return [line for line in out.splitlines() if line]


def current_branch(root: Path) -> str:
    """Return the current branch name, or ``detached`` if not on one."""
    if not is_git_repo(root):
        return "detached"
    try:
        out = run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    except GitRepoError:
        return "detached"
    return out.strip() or "detached"


def has_staged_changes(root: Path) -> bool:
    """Return True if there are any staged changes."""
    if not is_git_repo(root):
        return False
    try:
        out = run_git(["diff", "--cached", "--name-only"], root)
    except GitRepoError:
        return False
    return bool(out.strip())


def push(root: Path, *, remote: str = "origin", branch: str | None = None) -> str:
    """Push the current branch (or ``branch``) to ``remote``. Returns stdout."""
    if branch is None:
        branch = current_branch(root)
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    result = subprocess.run(
        ["git", "push", remote, branch],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise GitRepoError(
            f"git push failed: {result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout


__all__ = [
    "GitRepoError",
    "current_branch",
    "diff_between",
    "diff_staged",
    "diff_unstaged",
    "has_staged_changes",
    "is_git_repo",
    "push",
    "run_git",
    "status_porcelain",
]
