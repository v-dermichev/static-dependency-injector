"""Integration: dependency_injector container features still work through the
wrapper layer. We do not duplicate dependency_injector's own suite."""
from __future__ import annotations

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Cfg:
    def __init__(self, url: str) -> None:
        self.url = url


class TestContainerIntrospection:
    def test_providers_mapping_lists_declared(self) -> None:
        class C(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "u://")
            made: dict[str, int] = sp.Factory(lambda: {"a": 1})

        assert {"cfg", "made"} <= set(dict(C.providers))

    def test_cls_and_inherited_providers(self) -> None:
        class Parent(StaticDeclarativeContainer):
            a: int = sp.Object(1)

        class Child(Parent):
            b: int = sp.Object(2)

        assert "b" in dict(Child.cls_providers)
        assert "a" in dict(Child.inherited_providers)
        assert Child.a == 1  # inherited provider resolves
        assert Child.b == 2
