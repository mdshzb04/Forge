"""Background worker pool for executing non-blocking tasks."""



from __future__ import annotations

import asyncio
import logging

from forgecli.scheduler.task import BackgroundTask

logger = logging.getLogger("forge.scheduler.worker")





class WorkerPool:

    """Manages a pool of async workers to execute background tasks."""



    def __init__(self, concurrency: int = 2) -> None:

        self.concurrency = concurrency

        self._queue: asyncio.Queue[BackgroundTask] = asyncio.Queue()

        self._workers: list[asyncio.Task[None]] = []

        self._running = False



    def submit(self, task: BackgroundTask) -> None:

        """Submit a background task for execution."""

        self._queue.put_nowait(task)

        logger.debug("Submitted task %s to worker pool.", task.name)



    async def start(self) -> None:

        """Start the worker pool."""

        if self._running:

            return

        self._running = True

        for i in range(self.concurrency):

            task = asyncio.create_task(self._worker_loop(i))

            self._workers.append(task)

        logger.info("Worker pool started with %d workers.", self.concurrency)



    async def stop(self) -> None:

        """Stop the worker pool and wait for running tasks to finish."""

        self._running = False

        for _ in range(self.concurrency):



            pass





        for worker in self._workers:

            worker.cancel()



        await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()

        logger.info("Worker pool stopped.")



    async def _worker_loop(self, worker_id: int) -> None:

        """Main loop for a single worker."""

        while self._running:

            try:

                task = await self._queue.get()

                try:

                    logger.debug("Worker %d executing task %s", worker_id, task.name)

                    await task.func(*task.args, **task.kwargs)

                except Exception as e:

                    logger.error("Worker %d failed to execute task %s: %s", worker_id, task.name, e)

                finally:

                    self._queue.task_done()

            except asyncio.CancelledError:

                break

            except Exception as e:

                logger.error("Worker %d encountered error in loop: %s", worker_id, e)

