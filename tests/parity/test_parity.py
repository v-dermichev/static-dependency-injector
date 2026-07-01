"""Parity: for equivalent declarations, ``static_dependency_injector`` produces
the same resolved results and lifecycle behaviour as raw ``dependency_injector``.

Access differs by design - raw di returns a *provider* you call (``Di.x()``);
static returns the resolved *value* (``St.x``) - so the assertions compare
``Di.x()`` against ``St.x``.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Iterator
from typing import Any

from dependency_injector import containers, providers

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Cfg:
    def __init__(self, url: str = "u") -> None:
        self.url = url


class _Db:
    def __init__(self, config: _Cfg) -> None:
        self.config = config


class TestValueParity:
    def test_object(self) -> None:
        class Di(containers.DeclarativeContainer):
            val = providers.Object("hello")

        class St(StaticDeclarativeContainer):
            val: str = sp.Object("hello")

        assert Di.val() == St.val == "hello"

    def test_callable(self) -> None:
        class Di(containers.DeclarativeContainer):
            v = providers.Callable(lambda a, b: a + b, 2, 3)

        class St(StaticDeclarativeContainer):
            v: int = sp.Callable(lambda a, b: a + b, 2, 3)

        assert Di.v() == St.v == 5

    def test_coroutine(self) -> None:
        async def make() -> int:
            return 7

        class Di(containers.DeclarativeContainer):
            c = providers.Coroutine(make)

        class St(StaticDeclarativeContainer):
            c: Coroutine[Any, Any, int] = sp.Coroutine(make)

        assert asyncio.run(Di.c()) == asyncio.run(St.c) == 7

    def test_resource(self) -> None:
        def init() -> Iterator[str]:
            yield "ready"

        class Di(containers.DeclarativeContainer):
            r = providers.Resource(init)

        class St(StaticDeclarativeContainer):
            r: str = sp.Resource(init)

        assert Di.r() == St.r == "ready"


class TestLifecycleParity:
    def test_singleton_caches_the_same(self) -> None:
        class Di(containers.DeclarativeContainer):
            cfg = providers.Singleton(_Cfg)

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        assert (Di.cfg() is Di.cfg()) is (St.cfg is St.cfg) is True
        assert Di.cfg().url == St.cfg.url

    def test_factory_new_each_the_same(self) -> None:
        class Di(containers.DeclarativeContainer):
            cfg = providers.Factory(_Cfg)

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Factory(_Cfg)

        assert (Di.cfg() is Di.cfg()) is (St.cfg is St.cfg) is False
        assert Di.cfg().url == St.cfg.url


class TestWiringParity:
    def test_dependency_resolution_and_singleton_sharing(self) -> None:
        class Di(containers.DeclarativeContainer):
            cfg = providers.Singleton(_Cfg, "postgres://")
            db = providers.Singleton(_Db, config=cfg)

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "postgres://")
            db: _Db = sp.Singleton(_Db, config=cfg)

        assert Di.db().config.url == St.db.config.url == "postgres://"
        assert (Di.db().config is Di.cfg()) is (St.db.config is St.cfg) is True

    def test_factory_dependent_shares_singleton_dep_the_same(self) -> None:
        class Di(containers.DeclarativeContainer):
            cfg = providers.Singleton(_Cfg)
            db = providers.Factory(_Db, config=cfg)

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)
            db: _Db = sp.Factory(_Db, config=cfg)

        assert (Di.db() is Di.db()) is (St.db is St.db) is False
        assert (Di.db().config is Di.cfg()) is (St.db.config is St.cfg) is True


class TestOverrideParity:
    def test_provider_override_and_reset(self) -> None:
        class Di(containers.DeclarativeContainer):
            x = providers.Singleton(lambda: "real")

        class St(StaticDeclarativeContainer):
            x: str = sp.Singleton(lambda: "real")

        Di.x.override(providers.Object("fake"))
        St.set_overrides(x="fake")
        assert Di.x() == St.x == "fake"

        Di.x.reset_override()
        St.reset_override()
        assert Di.x() == St.x == "real"

    def test_whole_container_override(self) -> None:
        class DiFake(containers.DeclarativeContainer):
            cfg = providers.Object(_Cfg("fake"))

        class StFake(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Object(_Cfg("fake"))

        class Di(containers.DeclarativeContainer):
            cfg = providers.Singleton(_Cfg, "base")

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg, "base")

        Di.override(DiFake)
        St.override(StFake)
        assert Di.cfg().url == St.cfg.url == "fake"


class TestApiSurfaceParity:
    def test_same_container_introspection_api(self) -> None:
        class Di(containers.DeclarativeContainer):
            cfg = providers.Singleton(_Cfg)

        class St(StaticDeclarativeContainer):
            cfg: _Cfg = sp.Singleton(_Cfg)

        assert set(Di.providers) == set(St.providers) == {"cfg"}
        for name in ("override", "reset_override", "providers", "cls_providers"):
            assert hasattr(Di, name) and hasattr(St, name)
