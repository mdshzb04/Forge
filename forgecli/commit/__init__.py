"""Semantic commit, changelog, and release-notes tooling.

A small library that turns a git diff into a Conventional Commits
message, a changelog entry, and a release-notes document. The CLI
exposes it via ``forge commit``.
"""

from forgecli.commit.analyzer import (
    CommitAnalysis,
    CommitAnalyzer,
    CommitKind,
    FileChange,
    FileKind,
)
from forgecli.commit.changelog import Changelog, ChangelogEntry, ReleaseSection
from forgecli.commit.git_utils import (
    GitRepoError,
    current_branch,
    diff_staged,
    diff_unstaged,
    is_git_repo,
    push,
    status_porcelain,
)
from forgecli.commit.message import build_message, build_short_hash, build_subject
from forgecli.commit.release_notes import ReleaseNotes, build_release_notes

__all__ = [
    "Changelog",
    "ChangelogEntry",
    "CommitAnalysis",
    "CommitAnalyzer",
    "CommitKind",
    "FileChange",
    "FileKind",
    "GitRepoError",
    "ReleaseNotes",
    "ReleaseSection",
    "build_message",
    "build_release_notes",
    "build_short_hash",
    "build_subject",
    "current_branch",
    "diff_staged",
    "diff_unstaged",
    "is_git_repo",
    "push",
    "status_porcelain",
]
