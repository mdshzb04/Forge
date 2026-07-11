"""Unit tests for the Transport Layer and Daemon."""



from __future__ import annotations

import asyncio

import pytest

from forgecli.middleware.executor import PipelineExecutor
from forgecli.middleware.pipeline import MiddlewarePipeline
from forgecli.runtime_core.container import Container
from forgecli.transport.daemon import ForgeDaemon
from forgecli.transport.http_server import HttpServer


@pytest.mark.asyncio

async def test_http_server_lifecycle() -> None:

    Container()

    pipeline = MiddlewarePipeline()

    engine = PipelineExecutor(pipeline=pipeline)



    server = HttpServer(engine=engine, host="127.0.0.1", port=8000)



    assert not server.is_running





    await server.start()

    assert server.is_running

    assert server._server_task is not None





    await server.start()





    await server.stop()

    assert not server.is_running

    assert server._server_task is None





    await server.stop()





@pytest.mark.asyncio

async def test_daemon_lifecycle() -> None:

    Container()

    pipeline = MiddlewarePipeline()

    engine = PipelineExecutor(pipeline=pipeline)



    server = HttpServer(engine=engine)

    daemon = ForgeDaemon(server=server)





    daemon_task = asyncio.create_task(daemon.serve())





    await asyncio.sleep(0.1)



    assert server.is_running





    daemon._handle_signal(2)





    try:

        await asyncio.wait_for(daemon_task, timeout=1.0)

    except TimeoutError:

        pytest.fail("Daemon did not shut down in time")



    assert not server.is_running

