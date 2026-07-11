"""Unit tests for Phase 2 of the Forge Universal AI Runtime implementation."""



from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from forgecli.runtime_core.container import Container, Lifetime
from forgecli.runtime_core.context import RuntimeContext
from forgecli.runtime_core.errors import ConfigurationError
from forgecli.runtime_core.events import EventBus
from forgecli.runtime_core.factory import RuntimeFactory
from forgecli.runtime_core.interfaces import LifecycleAware, Provider, Service
from forgecli.runtime_core.lifecycle import LifecycleManager
from forgecli.runtime_core.provider_registry import ProviderRegistry
from forgecli.runtime_core.service_registry import ServiceRegistry


class MockServiceA(Service):

    """Simple service A for dependency injection verification."""



    pass





class MockServiceB(Service):

    """Simple service B depending on Service A."""



    def __init__(self, service_a: MockServiceA) -> None:

        self.service_a = service_a





class MockServiceC(Service):

    """Simple service C depending on Service B and Optional A."""



    def __init__(self, service_b: MockServiceB, service_a: MockServiceA | None = None) -> None:

        self.service_b = service_b

        self.service_a = service_a





class CircularA(Service):

    """Circular dependency class A."""



    def __init__(self, b: CircularB) -> None:

        self.b = b





class CircularB(Service):

    """Circular dependency class B."""



    def __init__(self, a: CircularA) -> None:

        self.a = a





class MockLifecycleService(Service, LifecycleAware):

    """Service tracking lifecycle callbacks."""



    def __init__(self) -> None:

        self.before_start_called = 0

        self.after_start_called = 0

        self.before_shutdown_called = 0

        self.after_shutdown_called = 0



    def on_before_start(self) -> None:

        self.before_start_called += 1



    def on_after_start(self) -> None:

        self.after_start_called += 1



    def on_before_shutdown(self) -> None:

        self.before_shutdown_called += 1



    def on_after_shutdown(self) -> None:

        self.after_shutdown_called += 1





class MockProvider(Provider):

    """Mock LLM Provider driver."""



    def __init__(self, name: str, caps: dict[str, Any]) -> None:

        self._name = name

        self._caps = caps



    @property

    def name(self) -> str:

        return self._name



    @property

    def capabilities(self) -> dict[str, Any]:

        return self._caps













def test_container_registration_and_lifetime_singleton() -> None:

    """Verify that singleton lifetime returns the identical instance."""

    container = Container()

    container.register(MockServiceA, lifetime=Lifetime.SINGLETON)



    inst1 = container.resolve(MockServiceA)

    inst2 = container.resolve(MockServiceA)



    assert isinstance(inst1, MockServiceA)

    assert inst1 is inst2





def test_container_registration_and_lifetime_transient() -> None:

    """Verify that transient lifetime returns a new instance each resolve."""

    container = Container()

    container.register(MockServiceA, lifetime=Lifetime.TRANSIENT)



    inst1 = container.resolve(MockServiceA)

    inst2 = container.resolve(MockServiceA)



    assert isinstance(inst1, MockServiceA)

    assert inst1 is not inst2





def test_container_registration_factory() -> None:

    """Verify factory-based dependency resolution."""

    container = Container()

    counter = 0



    def factory_func(c: Container) -> MockServiceA:

        nonlocal counter

        counter += 1

        return MockServiceA()



    container.register_factory(MockServiceA, factory_func, lifetime=Lifetime.TRANSIENT)



    inst1 = container.resolve(MockServiceA)

    inst2 = container.resolve(MockServiceA)



    assert counter == 2

    assert isinstance(inst1, MockServiceA)

    assert inst1 is not inst2





def test_container_registration_instance() -> None:

    """Verify pre-constructed object instance registration as a singleton."""

    container = Container()

    existing = MockServiceA()

    container.register_instance(MockServiceA, existing)



    resolved = container.resolve(MockServiceA)

    assert resolved is existing





def test_container_autowiring() -> None:

    """Verify automatic dependency resolution of constructor parameters."""

    container = Container()

    container.register(MockServiceA, lifetime=Lifetime.SINGLETON)

    container.register(MockServiceB, lifetime=Lifetime.TRANSIENT)





    inst_b = container.resolve(MockServiceB)

    assert isinstance(inst_b, MockServiceB)

    assert isinstance(inst_b.service_a, MockServiceA)





    container.register(MockServiceC, lifetime=Lifetime.TRANSIENT)

    inst_c = container.resolve(MockServiceC)

    assert isinstance(inst_c, MockServiceC)

    assert inst_c.service_a is not None





def test_container_scoped_lifetime() -> None:

    """Verify scoped lifetimes and context managers."""

    container = Container()

    container.register(MockServiceA, lifetime=Lifetime.SCOPED)





    with pytest.raises(ConfigurationError):

        container.resolve(MockServiceA)



    with container.scope("request-scope-1"):

        inst1 = container.resolve(MockServiceA)

        inst2 = container.resolve(MockServiceA)

        assert inst1 is inst2





    with container.scope("request-scope-2"):

        inst3 = container.resolve(MockServiceA)

        assert inst3 is not inst1





def test_container_circular_dependency_raises_configuration_error() -> None:

    """Verify that cyclic dependencies are caught and raise ConfigurationError."""

    container = Container()

    container.register(CircularA, lifetime=Lifetime.TRANSIENT)

    container.register(CircularB, lifetime=Lifetime.TRANSIENT)



    with pytest.raises(ConfigurationError) as exc:

        container.resolve(CircularA)



    assert "Circular dependency detected" in exc.value.message













def test_service_registry_operations() -> None:

    """Verify service registry, lookup, replacement, and unregister flows."""

    registry = ServiceRegistry()

    service = MockServiceA()



    registry.register("service-a", service, lazy=False)

    assert registry.exists("service-a")

    assert registry.resolve("service-a") is service

    assert "service-a" in registry.list_services()





    new_service = MockServiceA()

    registry.replace("service-a", new_service)

    assert registry.resolve("service-a") is new_service





    registry.unregister("service-a")

    assert not registry.exists("service-a")

    with pytest.raises(ConfigurationError):

        registry.resolve("service-a")





def test_service_registry_lazy_resolution() -> None:

    """Verify lazy-evaluated service construction."""

    registry = ServiceRegistry()

    counter = 0



    def factory() -> MockServiceA:

        nonlocal counter

        counter += 1

        return MockServiceA()



    registry.register("lazy-service", factory, lazy=True)

    assert counter == 0



    resolved = registry.resolve("lazy-service")

    assert counter == 1

    assert isinstance(resolved, MockServiceA)





    registry.resolve("lazy-service")

    assert counter == 1













def test_provider_registry() -> None:

    """Verify registration, query, defaults, and capabilities of LLM providers."""

    registry = ProviderRegistry()

    prov_anthropic = MockProvider("anthropic", {"thinking": True, "vision": True})

    prov_openai = MockProvider("openai", {"vision": True, "thinking": False})



    registry.register_provider("anthropic", prov_anthropic)

    registry.register_provider("openai", prov_openai)



    assert "anthropic" in registry.list_providers()

    assert registry.get_provider("anthropic") is prov_anthropic

    assert registry.capabilities("anthropic") == {"thinking": True, "vision": True}





    assert registry.default_provider() is prov_anthropic





    registry.set_default_provider("openai")

    assert registry.default_provider() is prov_openai





    registry.remove_provider("openai")

    assert "openai" not in registry.list_providers()













def test_runtime_context_and_cancellation() -> None:

    """Verify thread-safe context properties, state dictionaries, and cancellation."""

    ctx = RuntimeContext(

        session_id="session-1",

        workspace=Path("/workspace"),

        repository_root=Path("/repo"),

        current_provider="mock-prov",

        current_model="mock-model",

        metadata={"run": "alpha"},

    )



    assert ctx.session_id == "session-1"

    assert ctx.workspace == Path("/workspace")

    assert ctx.repository_root == Path("/repo")

    assert ctx.current_provider == "mock-prov"

    assert ctx.current_model == "mock-model"

    assert ctx.get_metadata("run") == "alpha"





    ctx.set_metadata("debug", True)

    assert ctx.get_metadata("debug") is True





    ctx.set_state("cache_key", "value")

    assert ctx.get_state("cache_key") == "value"





    token = ctx.cancellation_token

    assert not token.is_cancelled

    token.cancel()

    assert token.is_cancelled













def test_event_bus_priorities_and_unsubscribes() -> None:

    """Verify EventBus typed subscriptions, priorities, and handler cleanup."""

    event_bus = EventBus()

    execution_order = []



    class EventTest:

        pass



    def handler_low(evt: EventTest) -> None:

        execution_order.append("low")



    def handler_high(evt: EventTest) -> None:

        execution_order.append("high")



    event_bus.subscribe(EventTest, handler_low, priority=1)

    event_bus.subscribe(EventTest, handler_high, priority=100)





    event_bus.publish(EventTest())



    assert execution_order == ["high", "low"]





    execution_order.clear()

    event_bus.unsubscribe(EventTest, handler_high)

    event_bus.publish(EventTest())

    assert execution_order == ["low"]



    event_bus.shutdown()





def test_event_bus_emit_async() -> None:

    """Verify async event dispatching in thread pool worker."""

    event_bus = EventBus(max_workers=2)

    handled = threading.Event()



    class AsyncEvent:

        pass



    def handler(evt: AsyncEvent) -> None:

        handled.set()



    event_bus.subscribe(AsyncEvent, handler)

    future = event_bus.emit_async(AsyncEvent())





    future.result(timeout=2.0)

    assert handled.is_set()



    event_bus.shutdown()













def test_lifecycle_manager_transitions() -> None:

    """Verify component state hooks trigger in sequence."""

    manager = LifecycleManager()

    service = MockLifecycleService()

    manager.register_component(service)



    before_start_flag = False

    after_start_flag = False



    def on_before_start() -> None:

        nonlocal before_start_flag

        before_start_flag = True



    def on_after_start() -> None:

        nonlocal after_start_flag

        after_start_flag = True



    manager.register_before_start(on_before_start)

    manager.register_after_start(on_after_start)



    assert not manager.is_running

    manager.startup()

    assert manager.is_running



    assert service.before_start_called == 1

    assert service.after_start_called == 1

    assert before_start_flag is True

    assert after_start_flag is True





    manager.shutdown()

    assert not manager.is_running

    assert service.before_shutdown_called == 1

    assert service.after_shutdown_called == 1













def test_runtime_factory_creation() -> None:

    """Verify Factory constructor resolutions from active DI Container."""

    container = Container()

    container.register(MockServiceA, lifetime=Lifetime.SINGLETON)

    container.register(MockServiceB, lifetime=Lifetime.TRANSIENT)



    factory = RuntimeFactory(container)

    resolved_b = factory.create(MockServiceB)



    assert isinstance(resolved_b, MockServiceB)

    assert isinstance(resolved_b.service_a, MockServiceA)













def test_container_registration_errors() -> None:

    """Verify Container raises ConfigurationError on invalid registration types."""

    container = Container()





    with pytest.raises(ConfigurationError):

        container.register(MockServiceA, "not-a-class")





    with pytest.raises(ConfigurationError):

        container.register_factory(MockServiceA, "not-callable")  # type: ignore





def test_container_autowire_unresolvable_param() -> None:

    """Verify auto-wiring raises ConfigurationError when parameter is unresolvable."""

    container = Container()



    class InnerDependency(Service):

        def __init__(self, unannotated_param) -> None:

            self.param = unannotated_param



    class UnresolvableService(Service):

        def __init__(self, dep: InnerDependency) -> None:

            self.dep = dep



    container.register(UnresolvableService)

    with pytest.raises(ConfigurationError):

        container.resolve(UnresolvableService)





def test_service_registry_edge_cases() -> None:

    """Verify ServiceRegistry edge cases and error triggers."""

    registry = ServiceRegistry()





    registry.register("service-1", MockServiceA())

    with pytest.raises(ConfigurationError):

        registry.register("service-1", MockServiceA())





    with pytest.raises(ConfigurationError):

        registry.resolve("service-2")





    def bad_factory() -> Any:

        return "not-a-service"



    registry.register("bad-service", bad_factory, lazy=True)

    with pytest.raises(ConfigurationError):

        registry.resolve("bad-service")





    def throwing_factory() -> Any:

        raise ValueError("construction failed")



    registry.register("throwing-service", throwing_factory, lazy=True)

    with pytest.raises(ConfigurationError):

        registry.resolve("throwing-service")





    registry._registry["invalid-service"] = 12345  # type: ignore

    with pytest.raises(ConfigurationError):

        registry.resolve("invalid-service")





    with pytest.raises(ConfigurationError):

        registry.replace("non-existent", MockServiceA())





    registry.clear()

    assert not registry.exists("service-1")





def test_provider_registry_edge_cases() -> None:

    """Verify ProviderRegistry validation checks."""

    registry = ProviderRegistry()





    with pytest.raises(ConfigurationError):

        registry.register_provider("invalid", "not-a-provider")  # type: ignore





    with pytest.raises(ConfigurationError):

        registry.get_provider("missing")





    with pytest.raises(ConfigurationError):

        registry.set_default_provider("missing")





    assert registry.default_provider() is None





def test_lifecycle_manager_edge_cases() -> None:

    """Verify LifecycleManager duplicate starts, stops, and reload cycles."""

    manager = LifecycleManager()

    service = MockLifecycleService()





    manager.register_component(service)

    manager.unregister_component(service)

    manager.startup()

    assert service.before_start_called == 0

    manager.shutdown()





    manager.startup()

    assert manager.is_running

    manager.startup()

    assert manager.is_running





    manager.shutdown()

    assert not manager.is_running

    manager.shutdown()





    class ThrowingLifecycleComponent(LifecycleAware):

        def on_before_start(self) -> None:

            raise RuntimeError("crash on start")

        def on_after_start(self) -> None:

            pass

        def on_before_shutdown(self) -> None:

            pass

        def on_after_shutdown(self) -> None:

            pass



    manager.register_component(ThrowingLifecycleComponent())

    manager.startup()

    assert manager.is_running

    manager.shutdown()





    manager.reload()





def test_event_bus_edge_cases() -> None:

    """Verify EventBus non-callable listener safety and exception resiliency."""

    event_bus = EventBus()





    with pytest.raises(TypeError):

        event_bus.subscribe(str, "not-a-callable")  # type: ignore





    execution_order = []

    def good_handler(evt: str) -> None:

        execution_order.append("good")



    def bad_handler(evt: str) -> None:

        raise ValueError("broken listener")



    event_bus.subscribe(str, bad_handler, priority=10)

    event_bus.subscribe(str, good_handler, priority=5)



    event_bus.publish("my-event")

    assert execution_order == ["good"]





    event_bus.unsubscribe(int, good_handler)



    event_bus.shutdown()





def test_runtime_context_telemetry_getters_setters() -> None:

    """Verify telemetry context mappings inside RuntimeContext."""

    ctx = RuntimeContext(

        session_id="s",

        workspace=Path("w"),

        repository_root=Path("r")

    )

    assert ctx.get_telemetry_context("metric", 0) == 0

    ctx.set_telemetry_context("metric", 42)

    assert ctx.get_telemetry_context("metric") == 42





    ctx.current_provider = "anthropic"

    ctx.current_model = "claude-3"

    assert ctx.current_provider == "anthropic"

    assert ctx.current_model == "claude-3"



