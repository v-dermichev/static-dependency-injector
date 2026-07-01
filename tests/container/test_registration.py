"""Container metaclass: lifting providers to resolved properties, registration
under a name, shared-by-name (first-writer-wins), inheritance, and that
non-provider attributes are left untouched."""
from __future__ import annotations

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
)


class TestProviderLifting:
    def test_declared_provider_resolves_as_value_not_provider(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object("v")

        assert C.val == "v"
        assert not isinstance(C.val, sp.Object)

    def test_non_provider_attrs_left_untouched(self) -> None:
        class C(StaticDeclarativeContainer):
            CONST = 123
            val = sp.Object(1)

            @staticmethod
            def helper() -> str:
                return "ok"

        assert C.CONST == 123
        assert C.helper() == "ok"
        assert C.val == 1

    def test_provider_names_reports_declared_providers(self) -> None:
        class C(StaticDeclarativeContainer):
            a = sp.Object(1)
            b = sp.Singleton(object)
            CONST = 9

        assert C._provider_names() == frozenset({"a", "b"})


class TestRegistration:
    def test_explicit_name_via_container_config(self) -> None:
        class C(StaticDeclarativeContainer):
            container_config = {"name": "explicit.box"}
            val = sp.Object(1)

        reg = StaticDeclarativeContainerMeta._REGISTRY
        assert "explicit.box" in reg
        assert "val" in reg["explicit.box"]

    def test_default_name_is_module_qualname(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object(1)

        keys = list(StaticDeclarativeContainerMeta._REGISTRY)
        assert any(key.endswith(".C") and "<locals>" in key for key in keys)


class TestSharedByName:
    def test_first_writer_wins(self) -> None:
        class C1(StaticDeclarativeContainer):
            container_config = {"name": "shared.fw"}
            val = sp.Object("first")

        class C2(StaticDeclarativeContainer):
            container_config = {"name": "shared.fw"}
            val = sp.Object("second")  # same name -> ignored

        assert C1.val == "first"
        assert C2.val == "first"

    def test_override_under_a_name_is_visible_through_every_class(self) -> None:
        class C1(StaticDeclarativeContainer):
            container_config = {"name": "shared.ovr"}
            val = sp.Object("orig")

        class C2(StaticDeclarativeContainer):
            container_config = {"name": "shared.ovr"}
            val = sp.Object("ignored")

        C1.set_overrides(val="changed")
        assert C2.val == "changed"  # shared binding under the name
        C1.clear_overrides("val")
        assert C2.val == "orig"


class TestInheritance:
    def test_subclass_without_providers_inherits_parent_resolution(self) -> None:
        class Parent(StaticDeclarativeContainer):
            container_config = {"name": "inh.parent"}
            val = sp.Object("parent-val")

        class Child(Parent):
            pass

        assert Child.val == "parent-val"
        assert "val" in Child._provider_names()
