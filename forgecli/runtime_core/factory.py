"""Factory implementation for the Universal AI Runtime.

Handles dynamic construction of runtime components by leveraging the DI container.
"""



from __future__ import annotations

from typing import TypeVar

from forgecli.runtime_core.container import Container
from forgecli.runtime_core.interfaces import Factory

T = TypeVar("T")





class RuntimeFactory(Factory):

    """Responsible for building runtime classes using dependency injection."""



    def __init__(self, container: Container) -> None:

        """Initialize the RuntimeFactory with a dependency injection container.

        Args:
            container: The active Dependency Injection Container.
        """

        self._container = container



    def create(self, class_type: type[T]) -> T:

        """Construct an instance of the class resolving all dependencies automatically.

        Args:
            class_type: The target class type to build.

        Returns:
            An instantiated object with all type-hint dependencies resolved.
        """

        return self._container.resolve(class_type)

