"""Per-provider-type lifecycle: factory vs singleton caching, thread/context
scopes, callables/coroutines, resources, selectors, dependencies."""
from __future__ import annotations

import asyncio
import contextvars
import itertools
import threading
from collections.abc import Iterator

import pytest
from dependency_injector.errors import Error

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestFactory:
    def test_builds_new_instance_each_access(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.Factory(list)

        first, second = C.item, C.item
        assert first == [] == second
        assert first is not second

    def test_is_lazy_until_first_access(self) -> None:
        calls = itertools.count()

        class C(StaticDeclarativeContainer):
            item = sp.Factory(lambda: next(calls))

        assert next(calls) == 0  # nothing built yet at declaration time
        _ = C.item
        assert next(calls) == 2  # one build happened between the two next() calls


class TestSingleton:
    def test_caches_single_instance(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.Singleton(object)

        assert C.item is C.item

    def test_thread_safe_singleton_caches_single_instance(self) -> None:
        class C(StaticDeclarativeContainer):
            item = sp.ThreadSafeSingleton(object)

        assert C.item is C.item


class TestScopedSingletons:
    def test_thread_local_singleton_is_per_thread(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            val = sp.ThreadLocalSingleton(lambda: next(counter))

        main = C.val
        assert C.val == main
        seen: dict[str, int] = {}

        def worker() -> None:
            seen["val"] = C.val

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert seen["val"] != main

    def test_context_local_singleton_is_per_context(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            val = sp.ContextLocalSingleton(lambda: next(counter))

        def resolve_twice() -> tuple[int, int]:
            return C.val, C.val

        # Each fresh context resolves its own instance; cached within a context.
        a1, a2 = contextvars.copy_context().run(resolve_twice)
        b1, b2 = contextvars.copy_context().run(resolve_twice)
        assert a1 == a2 and b1 == b2  # cached within a context
        assert a1 != b1  # distinct across contexts


class TestCallableAndCoroutine:
    def test_callable_invokes_function_with_args(self) -> None:
        class C(StaticDeclarativeContainer):
            added = sp.Callable(lambda a, b: a + b, 2, 3)

        assert C.added == 5

    def test_coroutine_resolves_to_awaitable(self) -> None:
        async def make() -> int:
            return 7

        class C(StaticDeclarativeContainer):
            coro = sp.Coroutine(make)

        assert asyncio.run(C.coro) == 7


class TestResourceSelectorDependency:
    def test_resource_provides_yielded_value(self) -> None:
        def init() -> Iterator[str]:
            yield "ready"

        class C(StaticDeclarativeContainer):
            res = sp.Resource(init)

        assert C.res == "ready"

    def test_selector_picks_provider_by_key(self) -> None:
        state = {"key": "a"}

        class C(StaticDeclarativeContainer):
            chosen = sp.Selector(lambda: state["key"], a=sp.Object("A"), b=sp.Object("B"))

        assert C.chosen == "A"
        state["key"] = "b"
        assert C.chosen == "B"

    def test_dependency_raises_until_provided(self) -> None:
        class C(StaticDeclarativeContainer):
            dep = sp.Dependency(instance_of=int)

        with pytest.raises(Error):
            _ = C.dep
        C.set_overrides(dep=42)
        assert C.dep == 42

    def test_provider_base_resolves_via_override(self) -> None:
        class C(StaticDeclarativeContainer):
            x = sp.Provider()

        C.set_overrides(x="set")
        assert C.x == "set"
