"""Provider resolution and lifecycle: reads resolve to values, factory vs
singleton caching, thread/context scopes, callables/coroutines/resources/etc."""
from __future__ import annotations

import asyncio
import contextvars
import itertools
import threading
from collections.abc import Coroutine, Iterator
from typing import Any

import pytest
from dependency_injector.errors import Error

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class TestResolution:
    def test_object_returns_value(self) -> None:
        class C(StaticDeclarativeContainer):
            val: str = sp.Object("hello")

        assert C.val == "hello"

    def test_singleton_caches_single_instance(self) -> None:
        class C(StaticDeclarativeContainer):
            item: object = sp.Singleton(object)

        assert C.item is C.item

    def test_factory_builds_new_instance_each_access(self) -> None:
        class C(StaticDeclarativeContainer):
            item: dict[str, int] = sp.Factory(lambda: {"a": 1})

        first, second = C.item, C.item
        assert first == {"a": 1} == second
        assert first is not second

    def test_lazy_until_first_access(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            item: int = sp.Factory(lambda: next(counter))

        assert next(counter) == 0  # nothing built at declaration time
        _ = C.item
        assert next(counter) == 2


class TestScopes:
    def test_thread_safe_singleton_caches(self) -> None:
        class C(StaticDeclarativeContainer):
            item: object = sp.ThreadSafeSingleton(object)

        assert C.item is C.item

    def test_thread_local_singleton_is_per_thread(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            val: int = sp.ThreadLocalSingleton(lambda: next(counter))

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
            val: int = sp.ContextLocalSingleton(lambda: next(counter))

        def resolve_twice() -> tuple[int, int]:
            return C.val, C.val

        a1, a2 = contextvars.copy_context().run(resolve_twice)
        b1, b2 = contextvars.copy_context().run(resolve_twice)
        assert a1 == a2 and b1 == b2
        assert a1 != b1


class TestOtherProviders:
    def test_callable_invokes_function(self) -> None:
        class C(StaticDeclarativeContainer):
            added: int = sp.Callable(lambda a, b: a + b, 2, 3)

        assert C.added == 5

    def test_coroutine_resolves_to_awaitable(self) -> None:
        async def make() -> int:
            return 7

        class C(StaticDeclarativeContainer):
            coro: Coroutine[Any, Any, int] = sp.Coroutine(make)

        assert asyncio.run(C.coro) == 7

    def test_resource_provides_yielded_value(self) -> None:
        def init() -> Iterator[str]:
            yield "ready"

        class C(StaticDeclarativeContainer):
            res: str = sp.Resource(init)

        assert C.res == "ready"

    def test_selector_picks_provider_by_key(self) -> None:
        state = {"key": "a"}

        class C(StaticDeclarativeContainer):
            chosen: str = sp.Selector(lambda: state["key"], a=sp.Object("A"), b=sp.Object("B"))

        assert C.chosen == "A"
        state["key"] = "b"
        assert C.chosen == "B"

    def test_dependency_raises_until_provided(self) -> None:
        class C(StaticDeclarativeContainer):
            dep: int = sp.Dependency(instance_of=int)

        with pytest.raises(Error):
            _ = C.dep
        C.set_overrides(dep=42)
        assert C.dep == 42
