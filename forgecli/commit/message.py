"""Build a Conventional Commits message from a :class:`CommitAnalysis`."""

from __future__ import annotations

from forgecli.commit.analyzer import CommitAnalysis, CommitKind


def build_message(analysis: CommitAnalysis) -> str:
    """Return a full commit message (subject + body + footer)."""
    parts: list[str] = [analysis.summary]
    if analysis.body:
        parts.append("")
        parts.append(analysis.body)
    if analysis.breaking:
        parts.append("")
        parts.append("BREAKING CHANGE: this commit contains a breaking change.")
    return "\n".join(parts).rstrip() + "\n"


def build_subject(analysis: CommitAnalysis) -> str:
    """Return just the first line (subject) of the commit message."""
    return analysis.summary


def build_short_hash(analysis: CommitAnalysis) -> str:
    """Return a deterministic short hash derived from the analysis.

    Used to keep multiple invocations of ``forge commit`` on the same
    diff producing the same subject line (idempotency is helpful for
    changelog generation).
    """
    import hashlib

    payload = "|".join(
        [
            analysis.kind.value,
            analysis.scope or "",
            analysis.summary,
            ",".join(f"{c.path}:{c.insertions}:{c.deletions}" for c in analysis.files),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


__all__ = ["build_message", "build_short_hash", "build_subject"]


# Re-export for convenience.
_ = CommitKind
