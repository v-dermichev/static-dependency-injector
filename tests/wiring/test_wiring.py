"""End-to-end DI wiring: providers depending on other providers, lambdas and
plain callables as factories, factory/singleton interplay across a graph, and
that overriding a dependency flows through to its dependents."""
from __future__ import annotations

import itertools

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Config:
    def __init__(self, url: str) -> None:
        self.url = url


class _Repo:
    def __init__(self, config: _Config) -> None:
        self.config = config


class _Service:
    def __init__(self, repo: _Repo, label: str) -> None:
        self.repo = repo
        self.label = label


class TestProviderWiring:
    def test_provider_passed_as_dependency_is_resolved(self) -> None:
        class C(StaticDeclarativeContainer):
            config = sp.Singleton(_Config, "postgres://")
            repo = sp.Singleton(_Repo, config=config)

        assert isinstance(C.repo, _Repo)
        assert C.repo.config.url == "postgres://"

    def test_singleton_dependency_is_shared(self) -> None:
        class C(StaticDeclarativeContainer):
            config = sp.Singleton(_Config, "x://")
            repo = sp.Singleton(_Repo, config=config)

        assert C.repo.config is C.config  # same cached Config instance

    def test_three_level_graph_resolves(self) -> None:
        class C(StaticDeclarativeContainer):
            config = sp.Singleton(_Config, "u://")
            repo = sp.Singleton(_Repo, config=config)
            service = sp.Singleton(_Service, repo=repo, label="svc")

        assert C.service.label == "svc"
        assert C.service.repo is C.repo
        assert C.service.repo.config.url == "u://"

    def test_factory_dependent_rebuilds_but_shares_singleton_dep(self) -> None:
        class C(StaticDeclarativeContainer):
            config = sp.Singleton(_Config, "shared://")
            repo = sp.Factory(_Repo, config=config)  # new Repo each access

        a, b = C.repo, C.repo
        assert a is not b  # factory -> distinct repos
        assert a.config is b.config  # ...but the singleton config is shared


class TestLambdaAndCallableFactories:
    def test_lambda_factory(self) -> None:
        class C(StaticDeclarativeContainer):
            value = sp.Factory(lambda: {"made": True})

        assert C.value == {"made": True}

    def test_callable_with_positional_and_keyword_args(self) -> None:
        class C(StaticDeclarativeContainer):
            joined = sp.Callable(lambda *parts, sep: sep.join(parts), "a", "b", "c", sep="-")

        assert C.joined == "a-b-c"

    def test_lambda_dependency_wired_into_factory(self) -> None:
        class C(StaticDeclarativeContainer):
            prefix = sp.Singleton(lambda: "PRE")
            label = sp.Factory(lambda prefix: f"{prefix}:tag", prefix=prefix)

        assert C.label == "PRE:tag"


class TestOverridePropagation:
    def test_override_of_dependency_flows_into_factory_dependent(self) -> None:
        counter = itertools.count()

        class C(StaticDeclarativeContainer):
            config = sp.Singleton(_Config, "real://")
            repo = sp.Factory(lambda config: (config.url, next(counter)), config=config)

        assert C.repo[0] == "real://"
        C.set_overrides(config=_Config("fake://"))
        assert C.repo[0] == "fake://"  # factory rebuilt against overridden dependency
        C.clear_overrides("config")
        assert C.repo[0] == "real://"
