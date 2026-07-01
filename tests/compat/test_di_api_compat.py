"""Compatibility with dependency_injector's documented container API.

Groups: (1) di API that is *preserved* by the static layer (container override
tracking, ``reset_last_overriding``, nested containers); (2) di API that is
*deliberately* different because the container is static/class-level (provider
reads return values, instantiation is repurposed, resource lifecycle is not
driven).
"""
from __future__ import annotations

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Cfg:
    def __init__(self, url: str = "base") -> None:
        self.url = url


class TestContainerOverridePreserved:
    def test_override_records_overridden_and_reset_last(self) -> None:
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")

        class Fake(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Object(_Cfg("fake"))

        Base.override(Fake)
        assert Base.overridden  # di container-level state is recorded
        assert Base.cfg.url == "fake"  # ...and reflected in reads

        Base.reset_last_overriding()  # di's inherited method now works
        assert not Base.overridden
        assert Base.cfg.url == "base"

    def test_reset_override_clears_everything(self) -> None:
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")

        class Fake(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Object(_Cfg("fake"))

        Base.override(Fake)
        Base.set_overrides(cfg=_Cfg("scoped"))
        Base.reset_override()
        assert not Base.overridden
        assert Base.cfg.url == "base"


class TestResourceLifecycleDeprecated:
    def test_init_resources_raises_and_warns(self) -> None:
        class Services(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        with pytest.warns(DeprecationWarning), pytest.raises(NotImplementedError):
            Services.init_resources()  # ty:ignore[deprecated]

    def test_shutdown_resources_raises_and_warns(self) -> None:
        class Services(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        with pytest.warns(DeprecationWarning), pytest.raises(NotImplementedError):
            Services.shutdown_resources()  # ty:ignore[deprecated]


class TestNestedContainer:
    def test_sub_container_reads_and_override(self) -> None:
        class Inner(StaticDeclarativeContainer):
            x: int = sp.Object(7)
            y: str = sp.Singleton(lambda: "deep")

        class Outer(StaticDeclarativeContainer):
            inner: type[Inner] = sp.Container(Inner)
            top: int = sp.Object(1)

        assert Outer.inner is Inner
        assert Outer.inner.x == 7  # resolves through the sub-container
        assert Outer.inner.y == "deep"
        assert "inner" in Outer.providers  # registered as a provider

        with Inner.set_overrides(x=99):  # override flows through the nesting
            assert Outer.inner.x == 99
        assert Outer.inner.x == 7


class TestDeliberateModelDifferences:
    """di API that intentionally behaves differently for a static container."""

    def test_provider_attribute_reads_as_value_not_provider(self) -> None:
        class Services(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        # di: Services.cfg is a provider you call; static: it is the value.
        assert isinstance(Services.cfg, _Cfg)

    def test_instantiation_is_repurposed_to_override(self) -> None:
        class Services(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")

        # di: Services(...) builds a container instance; static: it applies value
        # overrides and returns a restoring handle usable as a context manager.
        with Services(cfg=_Cfg("temp")):
            assert Services.cfg.url == "temp"
        assert Services.cfg.url == "base"

    def test_direct_provider_assignment_rejected(self) -> None:
        class Services(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        with pytest.raises(AttributeError):
            Services.cfg = sp.Object(_Cfg("x"))  # type: ignore[misc]
