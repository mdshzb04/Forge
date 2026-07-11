"""Unit tests for the Plugin Hook System and Scheduler frameworks."""



from __future__ import annotations

import asyncio

import pytest

from forgecli.plugins.hook import HookEvent, HookManager
from forgecli.scheduler.scheduler import Scheduler
from forgecli.scheduler.task import BackgroundTask
from forgecli.scheduler.worker import WorkerPool


@pytest.mark.asyncio

async def test_hook_manager() -> None:

    manager = HookManager()



    events_received: list[HookEvent] = []



    async def on_test_event(event: HookEvent) -> None:

        events_received.append(event)



    async def on_test_event_fail(event: HookEvent) -> None:

        raise ValueError("simulated failure")



    manager.register("test_event", on_test_event)

    manager.register("test_event", on_test_event_fail)



    evt = HookEvent(name="test_event", sender="test", payload={"key": "val"})

    await manager.dispatch(evt)



    assert len(events_received) == 1

    assert events_received[0].payload["key"] == "val"





    manager.unregister("test_event", on_test_event)

    await manager.dispatch(HookEvent(name="test_event", sender="test"))

    assert len(events_received) == 1





@pytest.mark.asyncio

async def test_worker_pool() -> None:

    pool = WorkerPool(concurrency=2)

    await pool.start()





    await pool.start()



    task_completed = asyncio.Event()



    async def sample_task(x: int) -> None:

        assert x == 42

        task_completed.set()



    async def failing_task() -> None:

        raise RuntimeError("boom")



    pool.submit(BackgroundTask(name="success", func=sample_task, args=(42,)))

    pool.submit(BackgroundTask(name="fail", func=failing_task))





    try:

        await asyncio.wait_for(task_completed.wait(), timeout=1.0)

    except TimeoutError:

        pytest.fail("Task did not complete in time")



    await pool.stop()

    assert len(pool._workers) == 0





@pytest.mark.asyncio

async def test_scheduler() -> None:

    pool = WorkerPool(concurrency=1)

    await pool.start()



    scheduler = Scheduler(worker_pool=pool, tick_interval=0.05)



    execution_count = 0



    async def periodic_job() -> None:

        nonlocal execution_count

        execution_count += 1



    scheduler.schedule("my_job", interval_seconds=0.1, func=periodic_job)



    await scheduler.start()



    await asyncio.sleep(0.35)

    await scheduler.stop()

    await pool.stop()





    assert execution_count >= 2

