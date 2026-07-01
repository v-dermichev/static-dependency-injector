"""Provider wrappers for static containers.

Each public name (``Object``, ``Singleton``, …) is a **factory function** typed
``-> T`` - it lies about its return type so that a value-annotated field accepts
it (``db: Db = Singleton(Db)``), while returning a descriptor provider at runtime.
The descriptor's ``__get__`` resolves the dependency on class access; overriding
is done through the container's ``set_overrides`` (see the containers package).
"""
from collections.abc import Callable as _Fn
from typing import Any

from dependency_injector import providers

# Providers registered as test-scoped (reset between tests by the pytest plugin).
_TEST_SCOPED: set[Any] = set()


class _ContainerProvider[T](providers.Provider[T]):
    """Descriptor mixin: reading a container attribute resolves the value."""

    def __get__(self, _obj: object, _owner: type | None = None) -> T:
        return self()


class _Object[T](_ContainerProvider[T], providers.Object[T]):
    pass


class _Factory[T](_ContainerProvider[T], providers.Factory[T]):
    pass


class _Singleton[T](_ContainerProvider[T], providers.Singleton[T]):
    pass


class _ThreadSafeSingleton[T](_ContainerProvider[T], providers.ThreadSafeSingleton[T]):
    pass


class _ThreadLocalSingleton[T](_ContainerProvider[T], providers.ThreadLocalSingleton[T]):
    pass


class _ContextLocalSingleton[T](_ContainerProvider[T], providers.ContextLocalSingleton[T]):
    pass


class _Callable[T](_ContainerProvider[T], providers.Callable[T]):
    pass


class _Coroutine[T](_ContainerProvider[T], providers.Coroutine[T]):
    pass


class _Resource[T](_ContainerProvider[T], providers.Resource[T]):
    pass


class _Dependency[T](_ContainerProvider[T], providers.Dependency[T]):
    pass


class _Selector[T](_ContainerProvider[T], providers.Selector[T]):
    pass


class _Provider[T](_ContainerProvider[T], providers.Provider[T]):
    pass


class _Container[C](providers.Provider[C]):
    """Nested static container. Reading it returns the *sub-container class*, so
    ``Outer.inner.x`` resolves the sub-provider's value through the sub-container's
    own descriptors. It does not use dependency_injector's ``providers.Container``
    (which copies the container by instantiating it - meaningless for a static,
    class-level container)."""

    def __init__(self, container_cls: type[C], /) -> None:
        self._static_cls = container_cls
        super().__init__()

    def __get__(self, _obj: object, _owner: type | None = None) -> type[C]:
        return self._static_cls

    def _provide(self, args: Any, kwargs: Any) -> type[C]:
        return self._static_cls


class _TestContextSingleton[T](_ContextLocalSingleton[T]):
    pass


# --- public factory functions (typed `-> T`, return a provider at runtime) ----
# ruff N802 (capitalised function name) is ignored for this module in pyproject.


def Object[T](provides: T, /) -> T:
    return _Object(provides)  # ty:ignore[invalid-return-type]


def Factory[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _Factory(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def Singleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _Singleton(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def ThreadSafeSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _ThreadSafeSingleton(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def ThreadLocalSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _ThreadLocalSingleton(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def ContextLocalSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _ContextLocalSingleton(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def Callable[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _Callable(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def Coroutine[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return _Coroutine(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def Resource[T](provides: _Fn[..., Any], /, *args: Any, **kwargs: Any) -> T:
    return _Resource(provides, *args, **kwargs)  # ty:ignore[invalid-return-type]


def Dependency[T](*, instance_of: type[T]) -> T:
    return _Dependency(instance_of=instance_of)  # ty:ignore[invalid-return-type]


def Selector[T](selector: Any, /, **providers_: Any) -> T:
    return _Selector(selector, **providers_)  # ty:ignore[invalid-return-type]


def Provider[T]() -> T:
    return _Provider()  # ty:ignore[invalid-return-type]


def Container[C](container_cls: type[C], /) -> type[C]:
    """Nest a static container as a provider: ``inner: type[Inner] =
    Container(Inner)`` makes ``Outer.inner.x`` resolve ``Inner.x``."""
    return _Container(container_cls)  # ty:ignore[invalid-return-type]


def TestContextSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    provider = _TestContextSingleton(provides, *args, **kwargs)
    _TEST_SCOPED.add(provider)
    return provider  # ty:ignore[invalid-return-type]
