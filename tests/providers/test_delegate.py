"""`Delegate(sibling)` wires a provider as an on-demand `Callable[[], T]` that
resolves the *current* value on each call (delegation), rather than capturing one
instance at wiring time."""
from __future__ import annotations

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
