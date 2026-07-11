"""Dependency Injection Container for the Universal AI Runtime.

Manages component lifetimes, scopes, and automated constructor resolution.
"""



from __future__ import annotations

import contextlib
import inspect
import threading
import types
from collections.abc import Callable, Generator
from enum import Enum
from typing import Any, TypeVar, Union, get_args, get_origin

from forgecli.runtime_core.errors import ConfigurationError

T = TypeVar("T")





class Lifetime(Enum):

    """Defines the cache and lifecycle rules for registered components."""



    SINGLETON = "singleton"

    SCOPED = "scoped"

    TRANSIENT = "transient"





def _unpack_optional(param_type: Any) -> Any:

    """Extract the primary type if the type annotation is Union or Optional."""

    origin = get_origin(param_type)

    is_union = origin is Union

    if hasattr(types, "UnionType"):

        is_union = is_union or (origin is types.UnionType)



    if is_union:

        args = get_args(param_type)



        non_none = [a for a in args if a is not type(None)]

        if non_none:

            return non_none[0]

    return param_type





class Container:

    """Lightweight thread-safe Dependency Injection container.

    Coordinates class instantiation, singleton caching, local scopes, and
    recursive constructor injection based on type annotations.
    """



    def __init__(self) -> None:

        """Initialize the Container."""

        self._lock = threading.RLock()

        self._registry: dict[Any, tuple[Lifetime, Any]] = {}

        self._singletons: dict[Any, Any] = {}

        self._scopes: dict[str, dict[Any, Any]] = {}

        self._current_scope_id: str | None = None

        self._resolution_stack: list[Any] = []



    def register(

        self,

        dependency_type: Any,

        concrete_type: Any = None,

        lifetime: Lifetime = Lifetime.SINGLETON,

    ) -> None:

        """Register a class implementation mapped to a type.

        Args:
            dependency_type: The type key (usually an interface).
            concrete_type: The implementation class to instantiate.
            lifetime: Lifetime rule.

        Raises:
            ConfigurationError: If registration targets are invalid.
        """

        concrete = concrete_type or dependency_type

        if not isinstance(concrete, type):

            raise ConfigurationError(

                f"Registration target for {dependency_type} must be a class type, got {type(concrete)}."

            )

        with self._lock:

            self._registry[dependency_type] = (lifetime, concrete)



    def register_factory(

        self,

        dependency_type: Any,

        factory: Callable[[Container], Any],

        lifetime: Lifetime = Lifetime.SINGLETON,

    ) -> None:

        """Register a callable factory to build the dependency.

        Args:
            dependency_type: The type key.
            factory: A callback accepting this container and returning the instance.
            lifetime: Lifetime rule.

        Raises:
            ConfigurationError: If the factory is not callable.
        """

        if not callable(factory):

            raise ConfigurationError(f"Factory for {dependency_type} must be callable.")

        with self._lock:

            self._registry[dependency_type] = (lifetime, factory)



    def register_instance(self, dependency_type: Any, instance: Any) -> None:

        """Register a pre-constructed object as a Singleton instance.

        Args:
            dependency_type: The type key.
            instance: The pre-instantiated object.
        """

        with self._lock:

            self._registry[dependency_type] = (Lifetime.SINGLETON, instance)

            self._singletons[dependency_type] = instance



    def begin_scope(self, scope_id: str) -> None:

        """Begin a scoped context mapping.

        Args:
            scope_id: The tracking ID for the new scope.
        """

        with self._lock:

            self._scopes[scope_id] = {}

            self._current_scope_id = scope_id



    def end_scope(self, scope_id: str) -> None:

        """End a scoped context, releasing cached instances.

        Args:
            scope_id: The tracking ID for the scope to clean.
        """

        with self._lock:

            self._scopes.pop(scope_id, None)

            if self._current_scope_id == scope_id:

                self._current_scope_id = None



    @contextlib.contextmanager

    def scope(self, scope_id: str) -> Generator[None, None, None]:

        """Context manager to wrap scope lifecycles.

        Args:
            scope_id: The tracking ID for the scope.
        """

        self.begin_scope(scope_id)

        try:

            yield

        finally:

            self.end_scope(scope_id)



    def resolve(self, dependency_type: type[T]) -> T:

        """Resolve a type dependency, checking caches and auto-wiring if needed.

        Args:
            dependency_type: The class or interface type to resolve.

        Returns:
            The instantiated component.

        Raises:
            ConfigurationError: If resolution hits cycle errors or resolution fails.
        """

        with self._lock:

            self._resolution_stack = []

            return self._resolve_impl(dependency_type)



    def _resolve_impl(self, dependency_type: Any) -> Any:

        """Recursive internal resolution worker."""

        if dependency_type in self._resolution_stack:

            cycle = " -> ".join([str(t) for t in [*self._resolution_stack, dependency_type]])

            raise ConfigurationError(f"Circular dependency detected: {cycle}")



        self._resolution_stack.append(dependency_type)

        try:



            if dependency_type in self._singletons:

                return self._singletons[dependency_type]





            if self._current_scope_id is not None:

                scope_cache = self._scopes[self._current_scope_id]

                if dependency_type in scope_cache:

                    return scope_cache[dependency_type]





            if dependency_type not in self._registry:



                if isinstance(dependency_type, type):

                    return self._autowire(dependency_type)

                raise ConfigurationError(

                    f"Dependency type {dependency_type} is not registered in the container."

                )



            lifetime, target = self._registry[dependency_type]





            if not isinstance(target, type) and not callable(target):

                return target





            instance = self._autowire(target) if isinstance(target, type) else target(self)





            if lifetime == Lifetime.SINGLETON:

                self._singletons[dependency_type] = instance

            elif lifetime == Lifetime.SCOPED:

                if self._current_scope_id is None:

                    raise ConfigurationError(

                        f"Cannot resolve scoped dependency {dependency_type} without an active scope."

                    )

                self._scopes[self._current_scope_id][dependency_type] = instance



            return instance

        finally:

            self._resolution_stack.pop()



    def _autowire(self, target: type[Any]) -> Any:

        """Resolve parameters recursively from type hints and instantiate target."""

        try:

            sig = inspect.signature(target.__init__)

        except (AttributeError, ValueError):



            return target()



        try:



            type_hints = inspect.get_annotations(target.__init__, eval_str=True)

        except Exception:



            type_hints = {}



        kwargs = {}

        for name, param in sig.parameters.items():

            if name == "self":

                continue



            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):

                continue



            param_type = type_hints.get(name)

            if param_type is not None:

                unpacked = _unpack_optional(param_type)

                try:

                    kwargs[name] = self._resolve_impl(unpacked)

                    continue

                except Exception:



                    if param.default is not inspect.Parameter.empty:

                        kwargs[name] = param.default

                        continue

                    raise



            if param.default is not inspect.Parameter.empty:

                kwargs[name] = param.default

            else:

                raise ConfigurationError(

                    f"Unable to auto-wire parameter '{name}' of class {target.__name__}: "

                    "no type annotation found or default value available."

                )



        return target(**kwargs)

