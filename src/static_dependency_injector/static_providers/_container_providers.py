from collections.abc import Callable as _Callable
from typing import Any

from dependency_injector import providers

OnSetHook = _Callable[[Any, Any], Any]


class _ContainerProvider[T](providers.Provider[T]):
    """Descriptor mixin for static-container providers.

    Reading a container attribute resolves the dependency (``__get__`` ->
    ``self()``), typed as ``T``. Overriding is done through the container's
    ``set_overrides`` / ``clear_overrides``; direct attribute assignment is
    intentionally not part of the typed API. ``on_set`` registers a hook run
    over the value before an override is applied.
    """

    _static_di_on_set: OnSetHook | None = None

    def on_set(self, hook: OnSetHook) -> OnSetHook:
        self._static_di_on_set = hook
        return hook

    def __get__(self, _: Any, __: Any = None) -> T:
        return self()


# --- Instance factories --------------------------------------------------


class Factory[T](_ContainerProvider[T], providers.Factory[T]):
    """``Factory``: builds a new instance on every access."""


class Singleton[T](_ContainerProvider[T], providers.Singleton[T]):
    """``Singleton``: one instance per container, cached after the first access."""


class ThreadSafeSingleton[T](_ContainerProvider[T], providers.ThreadSafeSingleton[T]):
    """``Singleton`` guarded by a lock while the instance is created."""


class ThreadLocalSingleton[T](_ContainerProvider[T], providers.ThreadLocalSingleton[T]):
    """``Singleton`` with a separate instance per thread."""


class ContextLocalSingleton[T](_ContainerProvider[T], providers.ContextLocalSingleton[T]):
    """``Singleton`` with a separate instance per ``contextvars`` context."""


# --- Calls ---------------------------------------------------------------


class Callable[T](_ContainerProvider[T], providers.Callable[T]):
    """``Callable``: calls a function with the given arguments and returns the result."""


class Coroutine[T](_ContainerProvider[T], providers.Coroutine[T]):
    """``async`` variant of ``Callable`` for coroutines; returns an awaitable."""


# --- Values, resources, dependencies -------------------------------------


class Object[T](_ContainerProvider[T], providers.Object[T]):
    """``Object``: returns the given value unchanged."""


class Resource[T](_ContainerProvider[T], providers.Resource[T]):
    """``Resource``: a resource with init/teardown (generator or context manager)."""


class Dependency[T](_ContainerProvider[T], providers.Dependency[T]):
    """``Dependency``: declares a dependency that the caller must provide."""


class Selector[T](_ContainerProvider[T], providers.Selector[T]):
    """``Selector``: picks a provider by a selector value at runtime."""


class Provider[T](_ContainerProvider[T], providers.Provider[T]):
    """Base provider / escape hatch for custom implementations."""


# --- Test scope ----------------------------------------------------------


class TestContextSingleton[T](ContextLocalSingleton[T]):
    """``ContextLocalSingleton`` that is reset at the test boundary.

    Marked test-scoped: the bundled pytest plugin calls
    ``StaticDeclarativeContainer.reset_test_context()`` after each test, which
    resets such providers. A manual ``provider.reset()`` in a test ``finally``
    is therefore unnecessary - the next test gets a fresh instance on its own
    ``contextvars`` context.
    """

    __test__ = False  # keep pytest from collecting this Test-prefixed class
    _static_di_test_scoped: bool = True

