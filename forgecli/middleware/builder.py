"""Fluent pipeline builder for the Forge middleware engine.

Provides chainable methods to configure and instantiate a MiddlewarePipeline.
"""



from __future__ import annotations

from typing import Any

from forgecli.middleware.base import Middleware
from forgecli.middleware.pipeline import MiddlewarePipeline


class PipelineBuilder:

    """Provides a fluent API to build and configure a MiddlewarePipeline instance."""



    def __init__(self) -> None:

        """Initialize the PipelineBuilder."""

        self._middlewares: list[Middleware] = []



    def add(self, middleware_item: Middleware | type[Middleware], *args: Any, **kwargs: Any) -> PipelineBuilder:

        """Append a middleware instance or class to the pipeline chain.

        Args:
            middleware_item: An instance of Middleware or a Middleware class type.
            *args: Positional constructor arguments if a class type is supplied.
            **kwargs: Keyword constructor arguments if a class type is supplied.

        Returns:
            The builder instance for chaining.
        """

        if isinstance(middleware_item, type):

            instance = middleware_item(*args, **kwargs)

        else:

            instance = middleware_item



        self._middlewares.append(instance)

        return self



    def build(self) -> MiddlewarePipeline:

        """Construct the completed MiddlewarePipeline.

        Returns:
            The populated MiddlewarePipeline instance.
        """

        pipeline = MiddlewarePipeline()

        for mw in self._middlewares:

            pipeline.add(mw)

        return pipeline

