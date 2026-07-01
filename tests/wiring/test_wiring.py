"""DI wiring: providers depending on providers, shared singletons, lambda /
callable factories, multi-level graphs."""
from __future__ import annotations

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
    def test_provider_as_dependency_resolved(self) -> None:
        class C(StaticDeclarativeContainer):
            config: _Config = sp.Singleton(_Config, "postgres://")
            repo: _Repo = sp.Singleton(_Repo, config=config)

        assert isinstance(C.repo, _Repo)
        assert C.repo.config.url == "postgres://"

    def test_singleton_dependency_shared(self) -> None:
        class C(StaticDeclarativeContainer):
            config: _Config = sp.Singleton(_Config, "x://")
            repo: _Repo = sp.Singleton(_Repo, config=config)

        assert C.repo.config is C.config

    def test_three_level_graph(self) -> None:
        class C(StaticDeclarativeContainer):
            config: _Config = sp.Singleton(_Config, "u://")
            repo: _Repo = sp.Singleton(_Repo, config=config)
            service: _Service = sp.Singleton(_Service, repo=repo, label="svc")

        assert C.service.label == "svc"
        assert C.service.repo is C.repo
        assert C.service.repo.config.url == "u://"

    def test_factory_dependent_shares_singleton_dep(self) -> None:
        class C(StaticDeclarativeContainer):
            config: _Config = sp.Singleton(_Config, "shared://")
            repo: _Repo = sp.Factory(_Repo, config=config)

        a, b = C.repo, C.repo
        assert a is not b  # factory -> distinct repos
        assert a.config is b.config  # ...sharing the singleton config


class TestLambdaFactories:
    def test_lambda_factory(self) -> None:
        class C(StaticDeclarativeContainer):
            value: dict[str, bool] = sp.Factory(lambda: {"made": True})

        assert C.value == {"made": True}

    def test_lambda_dependency_wired(self) -> None:
        class C(StaticDeclarativeContainer):
            prefix: str = sp.Singleton(lambda: "PRE")
            label: str = sp.Factory(lambda prefix: f"{prefix}:tag", prefix=prefix)

        assert C.label == "PRE:tag"
