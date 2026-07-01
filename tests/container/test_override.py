"""set_overrides: scoped (context manager, auto-restore) and permanent, plus
unknown-name rejection and override propagation to dependents."""
from __future__ import annotations

import itertools

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestSetOverrides:
    def test_scoped_override_auto_restores(self) -> None:
        class C(StaticDeclarativeContainer):
            val: str = sp.Singleton(lambda: "orig")

        assert C.val == "orig"
        with C.set_overrides(val="fake"):
            assert C.val == "fake"
        assert C.val == "orig"

    def test_permanent_override(self) -> None:
        class C(StaticDeclarativeContainer):
            val: str = sp.Singleton(lambda: "orig")

        C.set_overrides(val="fake")
        assert C.val == "fake"

    def test_multiple_at_once(self) -> None:
        class C(StaticDeclarativeContainer):
            a: int = sp.Object(1)
            b: int = sp.Object(2)

        with C.set_overrides(a=10, b=20):
            assert (C.a, C.b) == (10, 20)
        assert (C.a, C.b) == (1, 2)

    def test_unknown_name_rejected_at_runtime(self) -> None:
        class C(StaticDeclarativeContainer):
            val: int = sp.Object(1)

        with pytest.raises(TypeError, match="no provider"):
            C.set_overrides(**{"bogus": 1})  # dynamic: bypass the static check

    def test_direct_assignment_is_rejected(self) -> None:
        class C(StaticDeclarativeContainer):
            val: int = sp.Object(1)

        with pytest.raises(AttributeError, match="set_overrides"):
            C.val = 2  # type-clean (int field) but rejected at runtime

    def test_override_with_value_wraps_in_object(self) -> None:
        class C(StaticDeclarativeContainer):
            val: str = sp.Singleton(lambda: "orig")

        with C.set_overrides(val="fake"):
            assert C.val == "fake"  # Object: the value as-is
        assert C.val == "orig"

    def test_override_with_provider_uses_it_directly(self) -> None:
        # a provider argument is used as-is (like dependency_injector's override):
        # a Factory yields a fresh value on each resolve, not a wrapped constant
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            val: str = sp.Singleton(lambda: "orig")

        with C.set_overrides(val=sp.Factory(lambda: f"fake-{next(counter)}")):
            first, second = C.val, C.val
            assert first.startswith("fake-")
            assert first != second  # Factory rebuilt each resolve (not an Object)
        assert C.val == "orig"

    def test_override_provider_changes_resolution_semantics(self) -> None:
        # the overriding provider's own semantics take over: a Factory overridden
        # with a Singleton resolves to one shared instance, and vice versa.
        class Obj:
            pass

        class Factoried(StaticDeclarativeContainer):
            x: Obj = sp.Factory(Obj)

        assert Factoried.x is not Factoried.x  # Factory: fresh each resolve
        with Factoried.set_overrides(x=sp.Singleton(Obj)):
            assert Factoried.x is Factoried.x  # now Singleton: one shared instance
        assert Factoried.x is not Factoried.x  # restored to Factory

        class Singletoned(StaticDeclarativeContainer):
            y: Obj = sp.Singleton(Obj)

        assert Singletoned.y is Singletoned.y  # Singleton: shared
        with Singletoned.set_overrides(y=sp.Factory(Obj)):
            assert Singletoned.y is not Singletoned.y  # now Factory: fresh
        assert Singletoned.y is Singletoned.y  # restored to Singleton

    def test_nested_scopes_stack(self) -> None:
        class C(StaticDeclarativeContainer):
            val: str = sp.Singleton(lambda: "orig")

        with C.set_overrides(val="a"):
            with C.set_overrides(val="b"):
                assert C.val == "b"
            assert C.val == "a"  # inner exit restores outer, not original
        assert C.val == "orig"


class TestOverridePropagation:
    def test_override_of_dependency_reaches_factory_dependent(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            seed: str = sp.Singleton(lambda: "real")
            built: str = sp.Factory(lambda seed: f"{seed}-{next(counter)}", seed=seed)

        assert C.built.startswith("real-")
        with C.set_overrides(seed="fake"):
            assert C.built.startswith("fake-")  # factory rebuilt against override
        assert C.built.startswith("real-")
