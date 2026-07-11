"""Abstract interfaces for the Universal AI Runtime.

Defines the contract types to decouple subsystem implementations.
"""



from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:

    from forgecli.runtime_core.context import RuntimeContext





class Service(ABC):  # noqa: B024

    """Abstract base class for all managed runtime services."""



    pass





class Provider(ABC):

    """Abstract base class for all LLM API drivers."""



    @property

    @abstractmethod

    def name(self) -> str:

        """The unique identifier name of the provider driver."""

        pass



    @property

    @abstractmethod

    def capabilities(self) -> dict[str, Any]:

        """A dictionary mapping capability keys to values or boolean flags."""

        pass





class Middleware(ABC):  # noqa: B024

    """Abstract base class for all interceptor middlewares in the pipeline."""



    pass





class Plugin(ABC):  # noqa: B024

    """Abstract base class for all marketplace plugins."""



    pass





class LifecycleAware(ABC):

    """Interface for services that respond to system lifecycle transitions."""



    @abstractmethod

    def on_before_start(self) -> None:

        """Triggered before the services start up."""

        pass



    @abstractmethod

    def on_after_start(self) -> None:

        """Triggered after services have successfully booted."""

        pass



    @abstractmethod

    def on_before_shutdown(self) -> None:

        """Triggered before the system begins teardown."""

        pass



    @abstractmethod

    def on_after_shutdown(self) -> None:

        """Triggered after all resources have been shut down."""

        pass





class EventHandler(ABC):

    """Interface for components that subscribe to the event bus."""



    @abstractmethod

    def __call__(self, event: Any) -> None:

        """Handle the broadcast event.

        Args:
            event: The dynamic event instance payload.
        """

        pass





class ContextAware(ABC):

    """Interface for components that require active runtime context injection."""



    @abstractmethod

    def set_context(self, context: RuntimeContext) -> None:

        """Inject the active runtime context.

        Args:
            context: The active thread-safe runtime context.
        """

        pass





class Factory(ABC):  # noqa: B024

    """Interface for components responsible for object instantiation."""



    pass

