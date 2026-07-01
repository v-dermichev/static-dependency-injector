"""Provider wrappers: shape (all are descriptor providers with ``on_set``) and
value resolution through a container, one parametrized case per provider type."""
from __future__ import annotations

from typing import Any

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.static_providers._container_providers import _ContainerProvider

_ALL_PROVIDERS = [
    sp.Object,
    sp.Factory,
    sp.Singleton,
    sp.ThreadSafeSingleton,
    sp.ThreadLocalSingleton,
    sp.ContextLocalSingleton,
    sp.TestContextSingleton,
    sp.Callable,
    sp.Coroutine,
    sp.Resource,
    sp.Dependency,
    sp.Selector,
    sp.Provider,
]


class TestProviderShape:
    @pytest.mark.parametrize("provider_cls", _ALL_PROVIDERS, ids=lambda c: c.__name__)
    def test_is_container_provider_with_on_set(self, provider_cls: type) -> None:
        assert issubclass(provider_cls, _ContainerProvider)
        assert hasattr(provider_cls, "on_set")


class TestProviderResolution:
    @pytest.mark.parametrize(
        "provider, expected",
        [
            pytest.param(sp.Object("hello"), "hello", id="Object"),
            pytest.param(sp.Callable(lambda: 7), 7, id="Callable"),
            pytest.param(sp.Factory(lambda: [1, 2]), [1, 2], id="Factory"),
            pytest.param(sp.Singleton(lambda: ("a",)), ("a",), id="Singleton"),
            pytest.param(sp.ThreadSafeSingleton(lambda: 5), 5, id="ThreadSafeSingleton"),
            pytest.param(sp.ThreadLocalSingleton(lambda: 9), 9, id="ThreadLocalSingleton"),
            pytest.param(sp.ContextLocalSingleton(lambda: {"k": 1}), {"k": 1}, id="ContextLocalSingleton"),
            pytest.param(sp.TestContextSingleton(lambda: 11), 11, id="TestContextSingleton"),
        ],
    )
    def test_resolves_to_expected_value(self, provider: Any, expected: Any) -> None:
        class C(StaticDeclarativeContainer):
            val = provider

        # The container attribute yields the resolved value, not the provider.
        assert C.val == expected
        assert not isinstance(C.val, _ContainerProvider)
