"""Thin wrapper around the ForgeGraph CLI.

This module delegates to the external compiled binary if one is on the PATH
(typically named ``graphify`` or ``forgegraph``).

* detects whether the binary is installed;
* invokes it as an async subprocess;
* parses the resulting ``graph.json`` and ``manifest.json`` into typed
  dataclasses that satisfy the :mod:`forgecli.graph.repository` interface.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forgecli.core.errors import ForgeCLIError

DEFAULT_OUTPUT_DIR = "forgegraph-out"
DEFAULT_GRAPH_FILE = "graph.json"
DEFAULT_MANIFEST_FILE = "manifest.json"


def _prepare_legacy_dir(root: Path) -> None:
    legacy = root / "graphify-out"
    target = root / DEFAULT_OUTPUT_DIR
    if target.exists() and not legacy.exists():
        try:
            target.rename(legacy)
        except Exception:
            pass


def _restore_target_dir(root: Path) -> None:
    legacy = root / "graphify-out"
    target = root / DEFAULT_OUTPUT_DIR
    if legacy.exists():
        try:
            if target.exists():
                shutil.rmtree(target)
            legacy.rename(target)
        except Exception:
            pass


class ForgeGraphNotFoundError(ForgeCLIError):
    """Raised when the executable is not on the user's PATH."""


class ForgeGraphInvocationError(ForgeCLIError):
    """Raised when the subprocess exits with a non-zero status."""


@dataclass(frozen=True)
class ForgeGraphArtifacts:
    """Filesystem locations of the artifacts produced by ForgeGraph."""

    root: Path
    output_dir: Path
    graph_json: Path
    manifest_json: Path
    graph_html: Path
    graph_report: Path

    @classmethod
    def for_root(cls, root: Path) -> ForgeGraphArtifacts:
        out = root / DEFAULT_OUTPUT_DIR
        return cls(
            root=root,
            output_dir=out,
            graph_json=out / DEFAULT_GRAPH_FILE,
            manifest_json=out / DEFAULT_MANIFEST_FILE,
            graph_html=out / "graph.html",
            graph_report=out / "GRAPH_REPORT.md",
        )


class ForgeGraphClient:
    """Async subprocess wrapper around the CLI.

    Instances are cheap to construct; they do not touch the filesystem
    until :meth:`detect`, :meth:`build`, :meth:`query`, etc. are called.
    """

    def __init__(
        self,
        *,
        executable: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self._executable = (
            executable
            or os.environ.get("FORGECLI_FORGEGRAPH_BIN")
            or os.environ.get("FORGECLI_GRAPHIFY_BIN", "graphify")
        )
        self._timeout = timeout

    @property
    def executable(self) -> str:
        return self._executable

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    async def detect(self) -> str | None:
        """Return the resolved path of the binary, or ``None``."""
        path = shutil.which(self._executable)
        return path

    async def is_installed(self) -> bool:
        """Return True if the binary is on the user's PATH."""
        return await self.detect() is not None

    async def version(self) -> str:
        """Return the version string reported by ``--version``."""
        binary = await self.detect()
        if binary is None:
            raise ForgeGraphNotFoundError(
                f"ForgeGraph executable {self._executable!r} not found on PATH"
            )
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise ForgeGraphInvocationError(
                f"Executable --version failed: {stderr.decode(errors='replace').strip()}"
            )
        return stdout.decode(errors="replace").strip() or "unknown"

    # ------------------------------------------------------------------
    # Build / update
    # ------------------------------------------------------------------

    async def build(
        self,
        root: Path,
        *,
        force: bool = False,
        no_cluster: bool = False,
        extra_args: Iterable[str] = (),
    ) -> ForgeGraphBuildOutcome:
        """Run ``extract <root>`` and return the parsed outcome."""
        binary = await self.detect()
        if binary is None:
            raise ForgeGraphNotFoundError(
                f"ForgeGraph executable {self._executable!r} not found on PATH"
            )

        root = root.resolve()
        _prepare_legacy_dir(root)
        args: list[str] = [
            binary,
            "extract",
            str(root),
            "--out",
            str(root),
        ]
        if force:
            args.append("--force")
        if no_cluster:
            args.append("--no-cluster")
        args.extend(extra_args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(root),
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            except TimeoutError as exc:
                proc.kill()
                raise ForgeGraphInvocationError(
                    f"ForgeGraph extract timed out after {self._timeout}s"
                ) from exc

            if proc.returncode != 0:
                raise ForgeGraphInvocationError(
                    "ForgeGraph extract failed (exit "
                    f"{proc.returncode}):\n{stderr.decode(errors='replace').strip()}"
                )
        finally:
            _restore_target_dir(root)

        artifacts = ForgeGraphArtifacts.for_root(root)
        if not no_cluster:
            await self.cluster_only(root)

        return ForgeGraphBuildOutcome(
            root=root,
            artifacts=artifacts,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )

    async def update(
        self,
        root: Path,
        *,
        force: bool = False,
        no_cluster: bool = False,
    ) -> ForgeGraphBuildOutcome:
        """Run ``update <root>`` and return the parsed outcome."""
        binary = await self.detect()
        if binary is None:
            raise ForgeGraphNotFoundError(
                f"ForgeGraph executable {self._executable!r} not found on PATH"
            )

        root = root.resolve()
        _prepare_legacy_dir(root)
        args: list[str] = [
            binary,
            "update",
            str(root),
        ]
        if force:
            args.append("--force")
        if no_cluster:
            args.append("--no-cluster")

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(root),
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            except TimeoutError as exc:
                proc.kill()
                raise ForgeGraphInvocationError(
                    f"ForgeGraph update timed out after {self._timeout}s"
                ) from exc

            if proc.returncode != 0:
                raise ForgeGraphInvocationError(
                    "ForgeGraph update failed (exit "
                    f"{proc.returncode}):\n{stderr.decode(errors='replace').strip()}"
                )
        finally:
            _restore_target_dir(root)

        artifacts = ForgeGraphArtifacts.for_root(root)
        return ForgeGraphBuildOutcome(
            root=root,
            artifacts=artifacts,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )

    async def cluster_only(
        self,
        root: Path,
        *,
        backend: str | None = None,
    ) -> str:
        """Run ``cluster-only <root>`` to update HTML viz and Graph Report."""
        args: list[str] = ["cluster-only", str(root.resolve())]
        if backend:
            args.append(f"--backend={backend}")
        return await self._run_capture(root, args)

    # ------------------------------------------------------------------
    # JSON parsers
    # ------------------------------------------------------------------

    @staticmethod
    def load_graph(path: Path) -> dict[str, Any]:
        """Read and return the raw ``graph.json`` payload."""
        if not path.exists():
            raise FileNotFoundError(f"graph.json not found at {path}")
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def load_manifest(path: Path) -> dict[str, Any]:
        """Read and return the raw ``manifest.json`` payload (may be missing)."""
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Query / explain / path / affected
    # ------------------------------------------------------------------

    async def _run_capture(
        self,
        root: Path,
        args: list[str],
        *,
        timeout: float | None = None,
    ) -> str:
        binary = await self.detect()
        if binary is None:
            raise ForgeGraphNotFoundError(
                f"ForgeGraph executable {self._executable!r} not found on PATH"
            )

        _prepare_legacy_dir(root)
        modified_args = []
        for arg in args:
            if DEFAULT_OUTPUT_DIR in arg:
                modified_args.append(arg.replace(DEFAULT_OUTPUT_DIR, "graphify-out"))
            else:
                modified_args.append(arg)

        try:
            proc = await asyncio.create_subprocess_exec(
                binary,
                *modified_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(root),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout or self._timeout
                )
            except TimeoutError as exc:
                proc.kill()
                raise ForgeGraphInvocationError(f"Subprocess {' '.join(modified_args[:1])} timed out") from exc
            if proc.returncode != 0:
                raise ForgeGraphInvocationError(
                    f"Subprocess exited with {proc.returncode}: {stderr.decode(errors='replace').strip()}"
                )
            return stdout.decode(errors="replace")
        finally:
            _restore_target_dir(root)

    async def query(
        self,
        root: Path,
        question: str,
        *,
        budget: int = 2000,
        graph_path: Path | None = None,
        dfs: bool = False,
    ) -> str:
        """Run query command and return its stdout text."""
        args: list[str] = ["query", question, "--budget", str(budget)]
        if graph_path is not None:
            args += ["--graph", str(graph_path)]
        if dfs:
            args.append("--dfs")
        return await self._run_capture(root, args)

    async def explain(
        self,
        root: Path,
        target: str,
        *,
        graph_path: Path | None = None,
    ) -> str:
        """Run explain command and return its stdout text."""
        args: list[str] = ["explain", target]
        if graph_path is not None:
            args += ["--graph", str(graph_path)]
        return await self._run_capture(root, args)

    async def path(
        self,
        root: Path,
        a: str,
        b: str,
        *,
        graph_path: Path | None = None,
    ) -> str:
        """Run path command and return its stdout text."""
        args: list[str] = ["path", a, b]
        if graph_path is not None:
            args += ["--graph", str(graph_path)]
        return await self._run_capture(root, args)

    async def affected(
        self,
        root: Path,
        target: str,
        *,
        relation: Iterable[str] | None = None,
        depth: int = 2,
        graph_path: Path | None = None,
    ) -> str:
        """Run affected command and return its stdout text."""
        args: list[str] = ["affected", target, "--depth", str(depth)]
        for rel in relation or ():
            args += ["--relation", rel]
        if graph_path is not None:
            args += ["--graph", str(graph_path)]
        return await self._run_capture(root, args)


@dataclass(frozen=True)
class ForgeGraphBuildOutcome:
    """The captured result of a build extract invocation."""

    root: Path
    artifacts: ForgeGraphArtifacts
    stdout: str
    stderr: str

    @property
    def graph_payload(self) -> dict[str, Any]:
        """The parsed ``graph.json`` payload (reads from disk on each call)."""
        return ForgeGraphClient.load_graph(self.artifacts.graph_json)

    @property
    def manifest_payload(self) -> dict[str, Any]:
        """The parsed ``manifest.json`` payload (may be empty)."""
        return ForgeGraphClient.load_manifest(self.artifacts.manifest_json)


__all__ = [
    "DEFAULT_GRAPH_FILE",
    "DEFAULT_MANIFEST_FILE",
    "DEFAULT_OUTPUT_DIR",
    "ForgeGraphArtifacts",
    "ForgeGraphBuildOutcome",
    "ForgeGraphClient",
    "ForgeGraphInvocationError",
    "ForgeGraphNotFoundError",
]
