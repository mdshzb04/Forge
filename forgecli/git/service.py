"""High-level git operations: stage, branch, push, diff."""



from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from forgecli.core.errors import GitError
from forgecli.core.service import Service
from forgecli.git.repo import GitRepo


class GitService(Service):

    """Convenience operations built on top of :class:`GitRepo`."""



    name = "git.service"



    def __init__(

        self,

        repo: GitRepo,

        *,

        default_branch: str = "main",

    ) -> None:

        super().__init__()

        self._repo = repo

        self._default_branch = default_branch



    @property

    def repo(self) -> GitRepo:

        return self._repo



    def stage(self, paths: Iterable[str | Path]) -> None:

        """Add ``paths`` to the index."""

        try:

            self._repo.raw.index.add([str(p) for p in paths])

        except Exception as exc:

            raise GitError(f"Failed to stage files: {exc}") from exc



    def current_branch(self) -> str:

        return self._repo._safe_branch()



    def diff(self, *args: Any) -> str:

        """Return ``git diff`` output; placeholder."""

        raise NotImplementedError("GitService.diff() is a scaffold placeholder")

