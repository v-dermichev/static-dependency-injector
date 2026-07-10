"""Provider wrappers for static containers.

Each public name (``Object``, ``Singleton``, …) is a **factory function** typed
``-> T`` - it lies about its return type so that a value-annotated field accepts
it (``db: Db = Singleton(Db)``), while returning a descriptor provider at runtime.
The descriptor's ``__get__`` resolves the dependency on class access; overriding
is done through the container's ``set_overrides`` (see the containers package).
"""
from collections.abc import Callable as _Fn
from typing import Any, cast

from dependency_injector import providers


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
    return cast(T, _Object(provides))


def Factory[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _Factory(provides, *args, **kwargs))


def Singleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _Singleton(provides, *args, **kwargs))


def ThreadSafeSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _ThreadSafeSingleton(provides, *args, **kwargs))


def ThreadLocalSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _ThreadLocalSingleton(provides, *args, **kwargs))


def ContextLocalSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _ContextLocalSingleton(provides, *args, **kwargs))


def Callable[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _Callable(provides, *args, **kwargs))


def Coroutine[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _Coroutine(provides, *args, **kwargs))


def Resource[T](provides: _Fn[..., Any], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _Resource(provides, *args, **kwargs))


def Dependency[T](*, instance_of: type[T]) -> T:
    return cast(T, _Dependency(instance_of=instance_of))


# Selector/Provider have no `provides` parameter, so `T` appears only in the
# return type and the field annotation supplies it (`x: Foo = Selector(...)` /
# `x: Foo = Provider()`). mypy/pyright flag that ("TypeVar appears only once");
# it is intentional and use-site-safe here (ty, the src gate, does not flag it).
def Selector[T](selector: Any, /, **providers_: Any) -> T:
    return cast(T, _Selector(selector, **providers_))


def Provider[T]() -> T:
    return cast(T, _Provider())


def Container[C](container_cls: type[C], /) -> type[C]:
    """Nest a static container as a provider: ``inner: type[Inner] =
    Container(Inner)`` makes ``Outer.inner.x`` resolve ``Inner.x``."""
    return cast(type[C], _Container(container_cls))


def TestContextSingleton[T](provides: _Fn[..., T], /, *args: Any, **kwargs: Any) -> T:
    return cast(T, _TestContextSingleton(provides, *args, **kwargs))


def Delegate[T](provided: T, /) -> _Fn[[], T]:
    """Wire a sibling provider as an on-demand resolver, typed ``Callable[[], T]``.

    In a container body a provider attribute is typed as its *resolved* value
    (``logger: Logger``), so dependency_injector's own delegation
    (``logger.provider``) does not type-check - ``Logger`` has no ``provider``.
    ``Delegate(logger)`` closes that gap: it accepts the value-typed sibling and
    returns a ``Callable[[], Logger]`` that resolves the *current* value on each
    call. Use it when the consumer must re-resolve rather than capture one instance
    - e.g. depending on a ``TestContextSingleton`` that is reset between tests::

        class Core(StaticDeclarativeContainer):
            logger: Logger = TestContextSingleton(Logger)
            waiter: Waiter = ContextLocalSingleton(Waiter, logger_resolver=Delegate(logger))

    At runtime ``provided`` is the provider object; it is delegated so the injected
    value is the provider itself (callable), not its resolved value.
    """
    return cast(_Fn[[], T], providers.Delegate(cast("providers.Provider[Any]", provided)))
