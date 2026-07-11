"""Decorators for the Forge middleware engine.

Provides annotations to declare execution priorities and register middleware classes.
"""



from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from forgecli.middleware.base import Middleware
from forgecli.middleware.registration import register_middleware_type

T = TypeVar("T", bound=type[Middleware])





def middleware(priority: int = 100, name: str | None = None) -> Callable[[T], T]:

    """Decorator to configure class priority and register a Middleware component.

    Args:
        priority: The execution precedence order.
        name: An optional unique registration name. Defaults to class name.

    Returns:
        The decorated Middleware class.
    """



    def decorator(cls: T) -> T:



        cls.priority = property(lambda self: priority)



        reg_name = name or cls.__name__

        register_middleware_type(reg_name, cls)

        return cls



    return decorator

