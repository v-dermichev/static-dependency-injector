"""Overriding providers: the ``set_overrides`` / ``clear_overrides``
classmethods and override propagation to dependents."""
from __future__ import annotations

import itertools

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestSetOverrides:
    def test_overrides_named_provider(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Singleton(lambda: "orig")

        C.set_overrides(val="fake")
        assert C.val == "fake"

    def test_overrides_several_at_once(self) -> None:
        class C(StaticDeclarativeContainer):
            a = sp.Object(1)
            b = sp.Object(2)

        C.set_overrides(a=10, b=20)
        assert (C.a, C.b) == (10, 20)

    def test_unknown_provider_rejected(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object(1)

        with pytest.raises(TypeError, match="no provider"):
            C.set_overrides(bogus=1)


class TestClearOverrides:
    def test_reset_named(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Singleton(lambda: "orig")

        C.set_overrides(val="fake")
        C.clear_overrides("val")
        assert C.val == "orig"

    def test_reset_all_when_no_names(self) -> None:
        class C(StaticDeclarativeContainer):
            a = sp.Singleton(lambda: "a0")
            b = sp.Singleton(lambda: "b0")

        C.set_overrides(a="a1", b="b1")
        C.clear_overrides()
        assert (C.a, C.b) == ("a0", "b0")

    def test_reset_is_safe_when_not_overridden(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Singleton(lambda: "orig")

        C.clear_overrides()  # nothing overridden - must not raise
        assert C.val == "orig"

    def test_unknown_provider_rejected(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object(1)

        with pytest.raises(TypeError, match="no provider"):
            C.clear_overrides("bogus")


class TestOverrideRebuildsDependents:
    def test_factory_dependent_picks_up_overridden_dependency(self) -> None:
        marker = itertools.count()

        class C(StaticDeclarativeContainer):
            seed = sp.Singleton(lambda: "real")
            # a factory that reads the seed on every build
            built = sp.Factory(lambda seed: f"{seed}-{next(marker)}", seed=seed)

        assert C.built.startswith("real-")
        C.set_overrides(seed="fake")
        assert C.built.startswith("fake-")  # rebuilt against the override
        C.clear_overrides("seed")
        assert C.built.startswith("real-")
