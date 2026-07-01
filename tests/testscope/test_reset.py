"""Test-scoped DI: ``TestContextSingleton`` is reset by ``reset_test_context``
(a plain ``Singleton`` survives), plus the bundled plugin's teardown hook."""
from __future__ import annotations

import itertools

from static_dependency_injector import _pytest_plugin
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestResetBehaviour:
    def test_resets_test_scoped_keeps_singleton(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            scoped: int = sp.TestContextSingleton(lambda: next(counter))
            single: int = sp.Singleton(lambda: next(counter))

        scoped0, single0 = C.scoped, C.single
        assert C.scoped == scoped0
        StaticDeclarativeContainer.reset_test_context()
        assert C.scoped != scoped0  # reset -> fresh
        assert C.single == single0  # singleton survives

    def test_reset_safe_when_never_built(self) -> None:
        class C(StaticDeclarativeContainer):
            scoped: object = sp.TestContextSingleton(object)

        StaticDeclarativeContainer.reset_test_context()

    def test_reset_spans_multiple_containers(self) -> None:
        count_a, count_b = itertools.count(), itertools.count()

        class A(StaticDeclarativeContainer):
            scoped: int = sp.TestContextSingleton(lambda: next(count_a))

        class B(StaticDeclarativeContainer):
            scoped: int = sp.TestContextSingleton(lambda: next(count_b))

        a0, b0 = A.scoped, B.scoped
        StaticDeclarativeContainer.reset_test_context()
        assert A.scoped != a0
        assert B.scoped != b0


class TestPluginTeardownHook:
    def test_teardown_hook_resets_test_scoped(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            scoped: int = sp.TestContextSingleton(lambda: next(counter))

        first = C.scoped
        item = type("_Item", (), {})()  # bare pytest Item stand-in
        _pytest_plugin.pytest_runtest_teardown(item)
        assert C.scoped != first
