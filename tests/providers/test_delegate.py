"""`Delegate(sibling)` wires a provider as an on-demand `Callable[[], T]` that
resolves the *current* value on each call (delegation), rather than capturing one
instance at wiring time."""
from __future__ import annotations

import contextvars
import threading
from collections.abc import Callable

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Logger:
    _n = 0

    def __init__(self) -> None:
        _Logger._n += 1
        self.id = _Logger._n


class _Waiter:
    def __init__(self, logger_resolver: Callable[[], _Logger]) -> None:
        self.logger_resolver = logger_resolver


class TestDelegate:
    def test_injects_a_callable_that_resolves_current_value(self) -> None:
        _Logger._n = 0

        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.TestContextSingleton(_Logger)
            waiter: _Waiter = sp.ContextLocalSingleton(_Waiter, logger_resolver=sp.Delegate(logger))

        waiter = Core.waiter
        # the wired value is a callable, not a captured instance
        assert callable(waiter.logger_resolver)
        assert waiter.logger_resolver() is Core.logger

    def test_reresolves_after_test_context_reset(self) -> None:
        _Logger._n = 0

        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.TestContextSingleton(_Logger)
            waiter: _Waiter = sp.ContextLocalSingleton(_Waiter, logger_resolver=sp.Delegate(logger))

        first = Core.waiter.logger_resolver().id
        Core.reset_test_context()
        second = Core.waiter.logger_resolver().id
        assert (first, second) == (1, 2)  # same waiter, freshly-resolved logger


class TestDelegatePreservesProviderSemantics:
    """Delegate injects the provider itself, resolved lazily in the calling scope -
    so the wrapped provider's per-call / per-scope behaviour is reproduced faithfully."""

    def test_delegate_of_factory_resolves_fresh_each_call(self) -> None:
        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.Factory(_Logger)
            waiter: _Waiter = sp.Singleton(_Waiter, logger_resolver=sp.Delegate(logger))

        resolve = Core.waiter.logger_resolver
        assert resolve() is not resolve()  # Factory: a new instance per call

    def test_delegate_of_singleton_resolves_the_shared_instance(self) -> None:
        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.Singleton(_Logger)
            waiter: _Waiter = sp.Singleton(_Waiter, logger_resolver=sp.Delegate(logger))

        resolve = Core.waiter.logger_resolver
        assert resolve() is resolve() is Core.logger  # same instance as a direct read

    def test_delegate_of_context_local_resolves_in_the_calling_scope(self) -> None:
        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.ContextLocalSingleton(_Logger)
            waiter: _Waiter = sp.Singleton(_Waiter, logger_resolver=sp.Delegate(logger))

        # within one context: the delegate resolves the same instance as a direct read
        def within() -> tuple[_Logger, _Logger]:
            return Core.logger, Core.waiter.logger_resolver()

        direct, via_delegate = contextvars.copy_context().run(within)
        assert direct is via_delegate

        # across contexts: distinct instances (resolved per calling scope)
        a = contextvars.copy_context().run(lambda: Core.waiter.logger_resolver().id)
        b = contextvars.copy_context().run(lambda: Core.waiter.logger_resolver().id)
        assert a != b

    def test_delegate_of_thread_local_resolves_per_thread(self) -> None:
        class Core(StaticDeclarativeContainer):
            logger: _Logger = sp.ThreadLocalSingleton(_Logger)
            waiter: _Waiter = sp.Singleton(_Waiter, logger_resolver=sp.Delegate(logger))

        main = Core.waiter.logger_resolver().id
        seen: dict[str, int] = {}

        def worker() -> None:
            seen["id"] = Core.waiter.logger_resolver().id

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert seen["id"] != main  # a distinct instance in another thread
