"""Release-note generation: turn a list of analyses into a Markdown doc.

A release notes document is more polished than a changelog: it has a
title, a date, an "Overview" paragraph, a "What's New" section with
features and fixes, a "Breaking Changes" callout (if any), a per-area
breakdown, and a contributor / file-statistics footer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from forgecli.commit.analyzer import CommitAnalysis, CommitKind


@dataclass
class ReleaseNotes:
    """A self-contained release-notes document."""

    version: str
    date: str
    analyses: list[CommitAnalysis]
    previous_version: str | None = None

    def render(self) -> str:
        """Return the release notes as a Markdown string."""
        lines: list[str] = []
        lines.append(f"# Release {self.version}")
        lines.append("")
        lines.append(f"_Released on {self.date}._")
        lines.append("")
        lines.extend(self._overview_paragraphs())
        lines.append("")
        if self._breaking():
            lines.append("## Breaking changes")
            lines.append("")
            for analysis in self._breaking():
                lines.append(f"- {analysis.summary}")
            lines.append("")
        if self._features():
            lines.append("## What's new")
            lines.append("")
            for analysis in self._features():
                lines.append(f"- {analysis.summary}")
            lines.append("")
        if self._fixes():
            lines.append("## Bug fixes")
            lines.append("")
            for analysis in self._fixes():
                lines.append(f"- {analysis.summary}")
            lines.append("")
        areas = self._areas()
        if len(areas) > 1:
            lines.append("## By area")
            lines.append("")
            for area, items in sorted(areas.items()):
                lines.append(f"### {area}")
                lines.append("")
                for analysis in items:
                    lines.append(f"- {analysis.summary}")
                lines.append("")
        lines.extend(self._statistics())
        if self.previous_version:
            lines.append("")
            lines.append(
                f"_Diff against {self.previous_version}: {self._diff_link_placeholder()}_"
            )
        return "\n".join(lines).rstrip() + "\n"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _breaking(self) -> list[CommitAnalysis]:
        return [a for a in self.analyses if a.breaking]

    def _features(self) -> list[CommitAnalysis]:
        return [a for a in self.analyses if a.kind is CommitKind.FEAT and not a.breaking]

    def _fixes(self) -> list[CommitAnalysis]:
        return [a for a in self.analyses if a.kind is CommitKind.FIX]

    def _areas(self) -> dict[str, list[CommitAnalysis]]:
        areas: dict[str, list[CommitAnalysis]] = {}
        for analysis in self.analyses:
            area = analysis.primary_scope or "misc"
            areas.setdefault(area, []).append(analysis)
        return areas

    def _overview_paragraphs(self) -> list[str]:
        if not self.analyses:
            return ["This release contains no user-facing changes."]
        counts: dict[CommitKind, int] = Counter(a.kind for a in self.analyses)
        parts: list[str] = []
        if counts[CommitKind.FEAT]:
            parts.append(f"{counts[CommitKind.FEAT]} new feature{'s' if counts[CommitKind.FEAT] != 1 else ''}")
        if counts[CommitKind.FIX]:
            parts.append(f"{counts[CommitKind.FIX]} bug fix{'es' if counts[CommitKind.FIX] != 1 else ''}")
        if counts[CommitKind.PERF]:
            parts.append(f"{counts[CommitKind.PERF]} performance improvement{'s' if counts[CommitKind.PERF] != 1 else ''}")
        if counts[CommitKind.REFACTOR]:
            parts.append(f"{counts[CommitKind.REFACTOR]} refactor{'s' if counts[CommitKind.REFACTOR] != 1 else ''}")
        if counts[CommitKind.DOCS]:
            parts.append(f"{counts[CommitKind.DOCS]} documentation update{'s' if counts[CommitKind.DOCS] != 1 else ''}")
        if not parts:
            parts.append(f"{len(self.analyses)} change{'s' if len(self.analyses) != 1 else ''}")
        total_files = sum(a.total_files for a in self.analyses)
        overview = "This release includes " + ", ".join(parts) + "."
        if total_files:
            overview += f" Touches {total_files} file{'s' if total_files != 1 else ''} across the codebase."
        if self._breaking():
            overview += " **It contains breaking changes** — see the section below."
        return [overview]

    def _statistics(self) -> list[str]:
        total_insertions = sum(a.stats.get("insertions", 0) for a in self.analyses)
        total_deletions = sum(a.stats.get("deletions", 0) for a in self.analyses)
        total_files = sum(a.stats.get("files", 0) for a in self.analyses)
        lines: list[str] = ["## Statistics", ""]
        lines.append(
            f"- Commits analyzed: {len(self.analyses)}"
        )
        lines.append(
            f"- Files touched: {total_files}"
        )
        lines.append(
            f"- Lines added: {total_insertions}"
        )
        lines.append(
            f"- Lines removed: {total_deletions}"
        )
        return lines

    def _diff_link_placeholder(self) -> str:
        return f"https://example.com/compare/v{self.previous_version}...v{self.version}"


def build_release_notes(
    version: str,
    analyses: list[CommitAnalysis],
    *,
    previous_version: str | None = None,
    today: str | None = None,
) -> ReleaseNotes:
    """Construct a :class:`ReleaseNotes` for ``version``."""
    return ReleaseNotes(
        version=version,
        date=today or date.today().isoformat(),
        analyses=list(analyses),
        previous_version=previous_version,
    )


__all__ = ["ReleaseNotes", "build_release_notes"]
