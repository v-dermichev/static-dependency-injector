"""Integration regression tests: dependency_injector behavior that flows through
our wrapper layer (descriptor providers + the metaclass) keeps working.

These guard *our* additions, not dependency_injector itself - that library has
its own extensive suite, which we deliberately do not duplicate.
"""
from __future__ import annotations

from dependency_injector import providers

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Cfg:
    def __init__(self, url: str) -> None:
        self.url = url


class TestContainerIntrospection:
    """The metaclass must not hide dependency_injector's provider registry."""

    def test_providers_mapping_lists_declared_providers(self) -> None:
        class C(StaticDeclarativeContainer):
            cfg = sp.Singleton(_Cfg, "u://")
            repo = sp.Factory(dict)

        assert {"cfg", "repo"} <= set(dict(C.providers))
        # entries are the provider objects, not resolved values
        assert isinstance(C.providers["cfg"], sp.Singleton)

    def test_cls_and_inherited_providers(self) -> None:
        class Parent(StaticDeclarativeContainer):
            a = sp.Object(1)

        class Child(Parent):
            b = sp.Object(2)

        assert "b" in dict(Child.cls_providers)
        assert "a" in dict(Child.inherited_providers)


class TestWrapperIsUsableDiProvider:
    """Our descriptor additions must not break a provider's plain di behavior."""

    def test_override_context_manager(self) -> None:
        p = sp.Singleton(_Cfg, "real://")
        with p.override(providers.Object(_Cfg("fake://"))):
            assert p().url == "fake://"
        assert p().url == "real://"

    def test_override_stacking_and_reset_last(self) -> None:
        p = sp.Object("base")
        p.override(providers.Object("A"))
        p.override(providers.Object("B"))
        assert p() == "B"
        p.reset_last_overriding()
        assert p() == "A"
        p.reset_override()
        assert p() == "base"


class TestInjection:
    def test_positional_and_keyword_args_are_injected(self) -> None:
        class Svc:
            def __init__(self, a: int, b: int, *, c: _Cfg) -> None:
                self.parts = (a, b, c)

        class C(StaticDeclarativeContainer):
            dep = sp.Singleton(_Cfg, "d://")
            svc = sp.Singleton(Svc, 1, 2, c=dep)

        assert C.svc.parts[0:2] == (1, 2)
        assert C.svc.parts[2] is C.dep  # provider dependency resolved + shared
