"""Tests for the ForgeGraph CLI wrapper."""



from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from forgecli.core.errors import ForgeCLIError
from forgecli.graph.forgegraph import (
    ForgeGraphArtifacts,
    ForgeGraphClient,
    ForgeGraphInvocationError,
    ForgeGraphNotFoundError,
)


def test_detect_returns_path_when_installed() -> None:

    import asyncio



    client = ForgeGraphClient(executable="forgegraph")

    with patch("shutil.which", return_value="/usr/bin/forgegraph"):

        path = asyncio.run(client.detect())

    assert path == "/usr/bin/forgegraph"





def test_is_installed_true_and_false() -> None:

    client = ForgeGraphClient()

    import asyncio



    with patch("shutil.which", return_value="/usr/bin/graphify"):

        assert asyncio.run(client.is_installed()) is True

    with patch("shutil.which", return_value="/usr/bin/forgegraph"):

        assert asyncio.run(client.is_installed()) is True

    with patch("shutil.which", return_value=None):

        assert asyncio.run(client.is_installed()) is False





def test_version_raises_when_missing(tmp_path: Path) -> None:

    client = ForgeGraphClient()

    import asyncio



    with patch("shutil.which", return_value=None):

        with pytest.raises(ForgeGraphNotFoundError):

            asyncio.run(client.version())





def test_artifacts_paths(tmp_path: Path) -> None:

    art = ForgeGraphArtifacts.for_root(tmp_path)

    assert art.output_dir == tmp_path / "forgegraph-out"

    assert art.graph_json == tmp_path / "forgegraph-out" / "graph.json"

    assert art.manifest_json == tmp_path / "forgegraph-out" / "manifest.json"

    assert art.graph_html == tmp_path / "forgegraph-out" / "graph.html"

    assert art.graph_report == tmp_path / "forgegraph-out" / "GRAPH_REPORT.md"





def test_load_graph_missing_file(tmp_path: Path) -> None:

    with pytest.raises(FileNotFoundError):

        ForgeGraphClient.load_graph(tmp_path / "graph.json")





def test_load_graph_round_trip(tmp_path: Path) -> None:

    payload = {"nodes": [{"id": "a"}], "links": [], "directed": False}

    path = tmp_path / "g.json"

    path.write_text(json.dumps(payload), encoding="utf-8")

    assert ForgeGraphClient.load_graph(path) == payload





def test_load_manifest_missing_returns_empty(tmp_path: Path) -> None:

    assert ForgeGraphClient.load_manifest(tmp_path / "missing.json") == {}





def test_build_raises_when_binary_missing(tmp_path: Path) -> None:

    import asyncio



    client = ForgeGraphClient()

    with patch("shutil.which", return_value=None):

        with pytest.raises(ForgeGraphNotFoundError):

            asyncio.run(client.build(tmp_path))





def test_build_invokes_subprocess(tmp_path: Path) -> None:

    import asyncio





    out = tmp_path / "forgegraph-out"

    out.mkdir()

    (out / "graph.json").write_text(

        json.dumps({"nodes": [], "links": [], "directed": False}),

        encoding="utf-8",

    )

    (out / "manifest.json").write_text("{}", encoding="utf-8")



    fake_proc = _FakeProc(returncode=0, stdout=b"ok", stderr=b"")



    async def fake_exec(*args, **kwargs):

        return fake_proc



    client = ForgeGraphClient(executable="/usr/bin/forgegraph")

    with (

        patch("shutil.which", return_value="/usr/bin/forgegraph"),

        patch(

            "asyncio.create_subprocess_exec",

            side_effect=fake_exec,

        ),

    ):

        outcome = asyncio.run(client.build(tmp_path))

    assert outcome.artifacts.graph_json.exists()

    assert "graph.json" in outcome.stdout or outcome.stdout == "ok"





def test_build_raises_on_nonzero_exit(tmp_path: Path) -> None:

    import asyncio



    fake_proc = _FakeProc(returncode=1, stdout=b"", stderr=b"boom")



    async def fake_exec(*args, **kwargs):

        return fake_proc



    client = ForgeGraphClient(executable="/usr/bin/forgegraph")

    with (

        patch("shutil.which", return_value="/usr/bin/forgegraph"),

        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),

    ):

        with pytest.raises(ForgeGraphInvocationError):

            asyncio.run(client.build(tmp_path))





def test_query_routes_to_subcommand(tmp_path: Path) -> None:

    import asyncio



    captured: dict[str, list[str]] = {}



    class _Proc:

        returncode = 0

        stdout = b"answer"

        stderr = b""



        async def communicate(self):

            return self.stdout, self.stderr



    async def fake_exec(*args, **kwargs):

        captured["args"] = list(args)

        return _Proc()



    client = ForgeGraphClient(executable="/usr/bin/forgegraph")

    with (

        patch("shutil.which", return_value="/usr/bin/forgegraph"),

        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),

    ):

        result = asyncio.run(client.query(tmp_path, "what?", budget=500))

    assert result == "answer"

    assert captured["args"][1:3] == ["query", "what?"]

    assert "--budget" in captured["args"]

    assert "500" in captured["args"]





class _FakeProc:

    def __init__(self, *, returncode: int, stdout: bytes, stderr: bytes) -> None:

        self.returncode = returncode

        self._stdout = stdout

        self._stderr = stderr



    async def communicate(self):

        return self._stdout, self._stderr



    def kill(self) -> None:  # pragma: no cover - only on timeout

        return None







_err = ForgeCLIError

_pytest = pytest

