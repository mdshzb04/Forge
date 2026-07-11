"""Task abstractions for background workers."""



from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass

class BackgroundTask:

    """A unit of work to be executed in the background."""



    name: str

    func: Callable[..., Awaitable[Any]]

    args: tuple[Any, ...] = field(default_factory=tuple)

    kwargs: dict[str, Any] = field(default_factory=dict)

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

