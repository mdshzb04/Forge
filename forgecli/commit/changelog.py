"""Changelog generation: keep-on-top CHANGELOG.md + per-release notes.

The :class:`Changelog` is intentionally simple: it appends a new entry
under an "Unreleased" section (or creates the section if missing),
groups entries by their conventional-commits kind, and exposes a
:meth:`release` method that lifts the unreleased entries into a
versioned block (e.g. ``## [1.2.0] - 2024-05-12``).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from forgecli.commit.analyzer import CommitAnalysis, CommitKind

_CHANGELOG_HEADER = "# Changelog\n\n"
_UNRELEASED_HEADER = "## [Unreleased]\n"
_KIND_SECTION_ORDER: tuple[CommitKind, ...] = (
    CommitKind.FEAT,
    CommitKind.FIX,
    CommitKind.PERF,
    CommitKind.REFACTOR,
    CommitKind.DOCS,
    CommitKind.TEST,
    CommitKind.BUILD,
    CommitKind.CI,
    CommitKind.CHORE,
    CommitKind.STYLE,
)
_KIND_HEADING: dict[CommitKind, str] = {
    CommitKind.FEAT: "### Features",
    CommitKind.FIX: "### Bug Fixes",
    CommitKind.PERF: "### Performance",
    CommitKind.REFACTOR: "### Refactoring",
    CommitKind.DOCS: "### Documentation",
    CommitKind.TEST: "### Tests",
    CommitKind.BUILD: "### Build System",
    CommitKind.CI: "### Continuous Integration",
    CommitKind.CHORE: "### Chores",
    CommitKind.STYLE: "### Style",
}


@dataclass
class ChangelogEntry:
    """A single bullet in the changelog."""

    analysis: CommitAnalysis
    section: str  # full markdown line, including bullet


@dataclass
class ReleaseSection:
    """A versioned block inside the changelog."""

    version: str
    date: str
    entries: list[ChangelogEntry]


class Changelog:
    """In-memory representation of a CHANGELOG.md file."""

    def __init__(self, unreleased: list[ChangelogEntry] | None = None,
                 releases: list[ReleaseSection] | None = None) -> None:
        self.unreleased: list[ChangelogEntry] = list(unreleased or [])
        self.releases: list[ReleaseSection] = list(releases or [])

    @classmethod
    def load(cls, path: Path) -> Changelog:
        """Read ``path`` and parse the entries."""
        if not path.exists():
            return cls()
        text = path.read_text(encoding="utf-8")
        return cls.parse(text)

    @classmethod
    def parse(cls, text: str) -> Changelog:
        """Parse a Markdown changelog string."""
        if not text.strip():
            return cls()
        lines = text.splitlines()
        # Drop the leading "# Changelog" header if present.
        if lines and lines[0].strip().lower() == "# changelog":
            lines = lines[1:]
        blocks = _split_into_blocks(lines)
        changelog = cls()
        for version, block_lines in blocks:
            entries = _parse_block(block_lines)
            if version == "unreleased":
                changelog.unreleased.extend(entries)
            else:
                version_label, release_date = _split_version(version)
                changelog.releases.append(
                    ReleaseSection(
                        version=version_label,
                        date=release_date,
                        entries=entries,
                    )
                )
        return changelog

    def add(self, analysis: CommitAnalysis) -> ChangelogEntry:
        """Append ``analysis`` to the Unreleased section."""
        entry = ChangelogEntry(
            analysis=analysis,
            section=_format_bullet(analysis),
        )
        self.unreleased.append(entry)
        return entry

    def release(self, version: str, *, today: str | None = None) -> ReleaseSection:
        """Move the current Unreleased section into a versioned block."""
        if not self.unreleased:
            raise ValueError("nothing to release: no unreleased entries")
        release = ReleaseSection(
            version=version,
            date=today or date.today().isoformat(),
            entries=list(self.unreleased),
        )
        self.releases.insert(0, release)
        self.unreleased = []
        return release

    def to_markdown(self) -> str:
        """Render the changelog to Markdown."""
        lines: list[str] = [_CHANGELOG_HEADER.strip(), ""]
        if self.unreleased:
            lines.append(_UNRELEASED_HEADER.rstrip())
            lines.append("")
            lines.extend(_render_entries(self.unreleased))
            lines.append("")
        for release in self.releases:
            header = f"## [{release.version}]"
            if release.date:
                header += f" - {release.date}"
            lines.append(header)
            lines.append("")
            lines.extend(_render_entries(release.entries))
            lines.append("")
        if lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"

    def save(self, path: Path) -> None:
        """Write the changelog back to ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_bullet(analysis: CommitAnalysis) -> str:
    """Render a single changelog bullet for ``analysis``."""
    subject = analysis.summary
    # Strip the "kind:" or "kind(scope):" prefix for cleaner changelog
    # bullets, since we group by kind in the output.
    prefix = analysis.kind.value
    if analysis.scope:
        prefix = f"{prefix}({analysis.scope})"
    if subject.startswith(f"{prefix}: ") or (subject.startswith(f"{prefix}:") and subject[len(prefix) + 1 :].startswith(" ")):
        subject = subject[len(prefix) + 2 :]
    if analysis.breaking:
        return f"- **BREAKING:** {subject}"
    return f"- {subject}"


def _render_entries(entries: Iterable[ChangelogEntry]) -> list[str]:
    """Render entries grouped by kind, with sub-headings per kind."""
    by_kind: dict[CommitKind, list[ChangelogEntry]] = defaultdict(list)
    for entry in entries:
        by_kind[entry.analysis.kind].append(entry)
    out: list[str] = []
    for kind in _KIND_SECTION_ORDER:
        bucket = by_kind.get(kind)
        if not bucket:
            continue
        out.append(_KIND_HEADING[kind])
        for entry in bucket:
            out.append(entry.section)
    # Append any unknown kinds at the end.
    for kind, bucket in by_kind.items():
        if kind in _KIND_SECTION_ORDER:
            continue
        out.append(_KIND_HEADING.get(kind, f"### {kind.value.capitalize()}"))
        for entry in bucket:
            out.append(entry.section)
    return out


_VERSION_HEADER = re.compile(r"^##\s+\[?(?P<version>[^\]]+?)\]?\s*(?:-\s*(?P<date>\S+))?\s*$")


def _split_into_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split the changelog body into ``(version, block_lines)`` chunks."""
    blocks: list[tuple[str, list[str]]] = []
    current_version: str | None = None
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_version is not None:
                blocks.append((current_version, current_lines))
            match = _VERSION_HEADER.match(line)
            if match is None:
                continue
            current_version = match.group("version").strip().lower()
            current_lines = []
        else:
            if current_version is not None:
                current_lines.append(line)
    if current_version is not None:
        blocks.append((current_version, current_lines))
    return blocks


def _split_version(label: str) -> tuple[str, str]:
    """Split ``"1.2.0 - 2024-05-12"`` into ``("1.2.0", "2024-05-12")``."""
    if " - " in label:
        version, date_value = label.split(" - ", 1)
        return version.strip(), date_value.strip()
    return label.strip(), ""


_KIND_BULLET_PREFIX = re.compile(r"^-\s+(\*\*BREAKING:\*\*\s+)?(.+?)\s*$")


def _parse_block(lines: list[str]) -> list[ChangelogEntry]:
    """Parse a list of lines into a flat list of :class:`ChangelogEntry`."""
    entries: list[ChangelogEntry] = []
    current_kind: CommitKind = CommitKind.CHORE
    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("### "):
            current_kind = _heading_to_kind(line)
            continue
        if line.startswith("- "):
            entries.append(
                ChangelogEntry(
                    analysis=_analysis_from_bullet(line, current_kind),
                    section=line,
                )
            )
    return entries


def _heading_to_kind(heading: str) -> CommitKind:
    for kind, label in _KIND_HEADING.items():
        if heading.strip() == label:
            return kind
    return CommitKind.CHORE


def _analysis_from_bullet(line: str, kind: CommitKind) -> CommitAnalysis:
    """Reconstruct a minimal :class:`CommitAnalysis` from a bullet line."""
    match = _KIND_BULLET_PREFIX.match(line)
    text = match.group(2) if match else line
    breaking = "**BREAKING:**" in line
    return CommitAnalysis(kind=kind, scope=None, summary=text, breaking=breaking)


__all__ = [
    "Changelog",
    "ChangelogEntry",
    "ReleaseSection",
]
