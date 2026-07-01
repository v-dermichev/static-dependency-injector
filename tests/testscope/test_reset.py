"""Test-scoped DI: ``TestContextSingleton`` is reset by ``reset_test_context``
(a plain ``Singleton`` survives), reachable from container / base / metaclass,
plus the bundled plugin's teardown hook."""
from __future__ import annotations

import itertools

from static_dependency_injector import _pytest_plugin
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
)


class TestMarkers:
    def test_marker_only_on_test_context_singleton(self) -> None:
        assert getattr(sp.TestContextSingleton, "_static_di_test_scoped", False) is True
        assert getattr(sp.ContextLocalSingleton, "_static_di_test_scoped", False) is False

    def test_not_collected_as_pytest_class(self) -> None:
        assert sp.TestContextSingleton.__test__ is False


class TestResetBehaviour:
    def test_resets_test_scoped_keeps_singleton(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(lambda: next(counter))
            single = sp.Singleton(lambda: next(counter))

        scoped0, single0 = C.scoped, C.single
        assert C.scoped == scoped0
        StaticDeclarativeContainerMeta.reset_test_context()
        assert C.scoped != scoped0  # reset -> fresh
        assert C.single == single0  # singleton survives

    def test_reset_safe_when_provider_never_built(self) -> None:
        class C(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(object)

        StaticDeclarativeContainerMeta.reset_test_context()

    def test_reset_spans_multiple_containers(self) -> None:
        count_a, count_b = itertools.count(), itertools.count()

        class A(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(lambda: next(count_a))

        class B(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(lambda: next(count_b))

        a0, b0 = A.scoped, B.scoped
        StaticDeclarativeContainerMeta.reset_test_context()
        assert A.scoped != a0
        assert B.scoped != b0


class TestResetEntryPoints:
    def test_callable_via_user_container(self) -> None:
        class C(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(object)

        first = C.scoped
        C.reset_test_context()
        assert C.scoped is not first

    def test_callable_via_base_container(self) -> None:
        class C(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(object)

        first = C.scoped
        StaticDeclarativeContainer.reset_test_context()
        assert C.scoped is not first


class TestPluginTeardownHook:
    def test_teardown_hook_resets_test_scoped(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(lambda: next(counter))

        first = C.scoped
        item = type("_Item", (), {})()  # bare pytest Item stand-in
        _pytest_plugin.pytest_runtest_teardown(item)
        assert C.scoped != first
