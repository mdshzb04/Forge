"""Exponential backoff retry policy for the Resilience framework."""



from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from forgecli.resilience.exceptions import MaxRetriesExceededError

T = TypeVar("T")

logger = logging.getLogger("forge.resilience.retry")





class RetryPolicy:

    """Implements an exponential backoff retry strategy."""



    def __init__(

        self,

        service: str,

        max_attempts: int = 3,

        base_delay: float = 1.0,

        max_delay: float = 10.0,

        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),

    ) -> None:

        """Initialize the RetryPolicy.

        Args:
            service: Name of the protected service.
            max_attempts: Maximum number of execution attempts.
            base_delay: Base delay in seconds.
            max_delay: Maximum backoff delay in seconds.
            retryable_exceptions: Tuple of exceptions that trigger a retry.
        """

        self.service = service

        self.max_attempts = max_attempts

        self.base_delay = base_delay

        self.max_delay = max_delay

        self.retryable_exceptions = retryable_exceptions



    async def execute_async(self, func: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:

        """Execute an asynchronous function with retries."""

        attempts = 0

        last_error: Exception | None = None



        while attempts < self.max_attempts:

            try:

                attempts += 1

                return await func(*args, **kwargs)

            except self.retryable_exceptions as e:

                last_error = e

                if attempts >= self.max_attempts:

                    break



                delay = min(self.base_delay * (2 ** (attempts - 1)), self.max_delay)

                logger.warning(

                    "Retry %d/%d for '%s' due to: %s. Waiting %.2fs...",

                    attempts, self.max_attempts, self.service, e, delay

                )

                await asyncio.sleep(delay)

            except Exception:



                raise



        raise MaxRetriesExceededError(self.service, attempts, last_error or Exception("Unknown error"))

