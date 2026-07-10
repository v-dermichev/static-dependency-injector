"""Subclassing (provider inheritance + subclass redeclaration) and whole-container
override via ``override`` / ``reset_override``."""
from __future__ import annotations

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer, copy


class _Cfg:
    def __init__(self, tag: str) -> None:
        self.tag = tag


class _Svc:
    def __init__(self, cfg: _Cfg) -> None:
        self.tag = cfg.tag


class TestSubclassing:
    def test_subclass_inherits_and_redeclares(self) -> None:
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")
            shared: int = sp.Object(1)

        class Child(Base):
            cfg: _Cfg = sp.Singleton(_Cfg, "child")  # redeclared in subclass
            extra: int = sp.Object(5)

        assert Base.cfg.tag == "base"
        assert Child.cfg.tag == "child"  # subclass wins
        assert Child.shared == 1  # inherited
        assert Child.extra == 5  # own
        assert Base.cfg.tag == "base"  # parent unaffected

    def test_plain_subclass_does_not_rewire_inherited_dependents(self) -> None:
        # Redeclaring only the dependency leaves an inherited dependent wired to
        # the original provider (matches dependency_injector's plain subclassing).
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")
            svc: _Svc = sp.Singleton(_Svc, cfg=cfg)

        class Child(Base):
            cfg: _Cfg = sp.Singleton(_Cfg, "child")  # dependency only

        assert Child.svc.tag == "base"  # svc still wired to Base.cfg

    def test_copy_rewires_redeclared_dependency_into_dependents(self) -> None:
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")
            svc: _Svc = sp.Singleton(_Svc, cfg=cfg)

        @copy(Base)
        class Child(Base):
            cfg: _Cfg = sp.Singleton(_Cfg, "child")

        assert Child.svc.tag == "child"  # dependent rewired to Child.cfg
        assert Base.svc.tag == "base"  # parent unaffected

    def test_copy_keeps_the_assignment_guard_strict(self) -> None:
        # The scoped rewiring bypass must not leak: direct assignment is still
        # rejected on a copied container.
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")

        @copy(Base)
        class Child(Base):
            cfg: _Cfg = sp.Singleton(_Cfg, "child")

        with pytest.raises(AttributeError):
            Child.cfg = sp.Object(_Cfg("x"))  # type: ignore[misc]
        assert Child.__dict__.get("_sdi_rewiring") is False  # bypass closed

    def test_set_overrides_on_subclass(self) -> None:
        class Base(StaticDeclarativeContainer):
            a: int = sp.Object(1)

        class Child(Base):
            b: int = sp.Object(2)

        with Child.set_overrides(a=10, b=20):  # inherited + own
            assert (Child.a, Child.b) == (10, 20)
        assert (Child.a, Child.b) == (1, 2)


class TestWholeContainerOverride:
    def test_override_reflected_in_reads(self) -> None:
        class Base(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")
            other: int = sp.Object(1)

        class Fake(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Object(_Cfg("fake"))

        Base.override(Fake)
        assert Base.cfg.tag == "fake"  # overridden by name
        assert Base.other == 1  # not in Fake -> untouched
        Base.reset_override()
        assert Base.cfg.tag == "base"
