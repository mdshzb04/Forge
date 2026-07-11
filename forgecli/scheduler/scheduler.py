"""Periodic task scheduler."""



from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from forgecli.scheduler.task import BackgroundTask
from forgecli.scheduler.worker import WorkerPool

logger = logging.getLogger("forge.scheduler")





@dataclass

class ScheduledJob:

    """A recurring job definition."""



    name: str

    func: Callable[..., Awaitable[Any]]

    interval_seconds: float





class Scheduler:

    """Manages periodic execution of scheduled jobs via a worker pool."""



    def __init__(self, worker_pool: WorkerPool, tick_interval: float = 1.0) -> None:

        self._pool = worker_pool

        self.tick_interval = tick_interval

        self._jobs: list[ScheduledJob] = []

        self._running = False

        self._main_task: asyncio.Task[None] | None = None



    def schedule(self, name: str, interval_seconds: float, func: Callable[..., Awaitable[Any]]) -> None:

        """Schedule a job to run periodically."""

        self._jobs.append(ScheduledJob(name, func, interval_seconds))

        logger.info("Scheduled job '%s' every %.1fs", name, interval_seconds)



    async def start(self) -> None:

        """Start the scheduler."""

        if self._running:

            return

        self._running = True

        self._main_task = asyncio.create_task(self._scheduler_loop())



    async def stop(self) -> None:

        """Stop the scheduler."""

        self._running = False

        if self._main_task:

            self._main_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):

                await self._main_task


            self._main_task = None



    async def _scheduler_loop(self) -> None:

        """Main loop that sleeps and triggers jobs."""

        if not self._jobs:

            return



        elapsed: dict[str, float] = {job.name: 0.0 for job in self._jobs}



        while self._running:

            try:

                await asyncio.sleep(self.tick_interval)

                for job in self._jobs:

                    elapsed[job.name] += self.tick_interval

                    if elapsed[job.name] >= job.interval_seconds:

                        elapsed[job.name] = 0.0

                        task = BackgroundTask(name=job.name, func=job.func)

                        self._pool.submit(task)

            except asyncio.CancelledError:

                break

            except Exception as e:

                logger.error("Scheduler encountered an error: %s", e)

