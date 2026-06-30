"""Unit tests for the provider wrappers: shape, value resolution, lifecycle
(factory / singleton / scopes), the set/del descriptor and the ``on_set`` hook -
all exercised through ``StaticDeclarativeContainer``."""
from __future__ import annotations

import asyncio
import itertools
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from dependency_injector.errors import Error

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
        # Every wrapper is a `_ContainerProvider` (descriptor + hook), so each
        # behaves identically as a container attribute.
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


class TestProviderLifecycle:
    def test_factory_builds_new_instance_each_access(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.Factory(list)

        first, second = C.item, C.item
        assert first == [] == second
        assert first is not second

    def test_singleton_caches_single_instance(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.Singleton(object)

        assert C.item is C.item

    def test_thread_safe_singleton_caches_single_instance(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.ThreadSafeSingleton(object)

        assert C.item is C.item

    def test_thread_local_singleton_is_per_thread(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            val = sp.ThreadLocalSingleton(lambda: next(counter))

        main = C.val
        assert C.val == main  # cached within the same thread
        seen: dict[str, int] = {}

        def worker() -> None:
            seen["val"] = C.val

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert seen["val"] != main  # another thread gets its own instance

    def test_coroutine_resolves_to_awaitable(self) -> None:
        async def make() -> int:
            return 7

        class C(StaticDeclarativeContainer):
            coro = sp.Coroutine(make)

        assert asyncio.run(C.coro) == 7

    def test_resource_provides_yielded_value(self) -> None:
        def init() -> Iterator[str]:
            yield "ready"

        class C(StaticDeclarativeContainer):
            res = sp.Resource(init)

        assert C.res == "ready"

    def test_selector_picks_provider_by_key(self) -> None:
        state = {"key": "a"}

        class C(StaticDeclarativeContainer):
            chosen = sp.Selector(
                lambda: state["key"],
                a=sp.Object("A"),
                b=sp.Object("B"),
            )

        assert C.chosen == "A"
        state["key"] = "b"
        assert C.chosen == "B"

    def test_dependency_resolves_only_once_provided(self) -> None:
        class C(StaticDeclarativeContainer):
            dep = sp.Dependency(instance_of=int)

        with pytest.raises(Error):
            _ = C.dep  # not provided -> error
        # Override-by-assignment goes through the metaclass runtime descriptor,
        # invisible to ty; hence the ty:ignore on every such write.
        C.dep = 42  # ty:ignore[invalid-assignment]
        assert C.dep == 42

    def test_provider_base_resolves_via_override(self) -> None:
        class C(StaticDeclarativeContainer):
            x = sp.Provider()

        C.x = "set"  # ty:ignore[invalid-assignment]
        assert C.x == "set"


class TestDescriptorSetDelete:
    def test_set_overrides_and_del_resets(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Singleton(lambda: "orig")

        assert C.val == "orig"
        C.val = "overridden"  # ty:ignore[invalid-assignment] - override via __set__
        assert C.val == "overridden"
        del C.val  # __delete__ -> reset_override
        assert C.val == "orig"


class TestOnSetHook:
    def test_hook_transforms_value_on_assignment(self) -> None:
        def double(_cls: Any, value: str) -> str:
            return value * 2

        provider = sp.Object("x")
        provider.on_set(double)

        class C(StaticDeclarativeContainer):
            val = provider

        assert C.val == "x"  # initial value - the hook does not touch reads
        C.val = "ab"  # ty:ignore[invalid-assignment]
        assert C.val == "abab"  # hook applied on assignment

    def test_without_hook_assignment_sets_value_directly(self) -> None:
        class C(StaticDeclarativeContainer):
            val = sp.Object("x")

        C.val = "y"  # ty:ignore[invalid-assignment]
        assert C.val == "y"

