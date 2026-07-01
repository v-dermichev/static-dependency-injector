"""The ``on_set`` hook: a function run over the value before an override is
applied (via assignment or ``set_overrides``)."""
from __future__ import annotations

from typing import Any

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestOnSetHook:
    def test_hook_transforms_value_on_override(self) -> None:
        def double(_cls: Any, value: str) -> str:
            return value * 2

        provider = sp.Object("x")
        provider.on_set(double)

        class C(StaticDeclarativeContainer):
            val = provider

        assert C.val == "x"  # initial value - the hook does not touch reads
        C.set_overrides(val="ab")
        assert C.val == "abab"  # hook applied on override

    def test_hook_receives_container_class(self) -> None:
        seen: dict[str, Any] = {}

        def capture(cls: Any, value: Any) -> Any:
            seen["cls"] = cls
            return value

        provider = sp.Object(0)
        provider.on_set(capture)

        class C(StaticDeclarativeContainer):
            val = provider

        C.set_overrides(val=1)
        assert seen["cls"] is C

    def test_without_hook_override_sets_value_directly(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object("x")

        C.set_overrides(val="y")
        assert C.val == "y"
