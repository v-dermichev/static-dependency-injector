"""`Container.provider.x` returns the provider object (not the resolved value),
for wiring one provider from another across a class boundary - e.g. an inherited
provider, whose bare name is out of scope in the subclass body."""
from __future__ import annotations

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Logger:
    pass


class _Svc:
    def __init__(self, logger: _Logger) -> None:
        self.logger = logger


class TestProviderGetter:
    def test_returns_provider_not_value(self) -> None:
        class Services(StaticDeclarativeContainer):
            logger: _Logger = sp.Singleton(_Logger)

        # reading gives the value; .provider gives the provider object (the same
        # object as the di dict `providers[name]`, which serves dynamic names)
        assert isinstance(Services.logger, _Logger)
        assert Services.provider.logger is Services.providers["logger"]

    def test_wires_inherited_provider_lazily(self) -> None:
        class Base(StaticDeclarativeContainer):
            logger: _Logger = sp.Singleton(_Logger)

        class Child(Base):
            svc: _Svc = sp.Singleton(_Svc, logger=Base.provider.logger)

        assert isinstance(Child.svc.logger, _Logger)
        assert Child.svc.logger is Child.logger  # shares the singleton

    def test_reflects_overrides(self) -> None:
        class Base(StaticDeclarativeContainer):
            logger: _Logger = sp.Singleton(_Logger)

        class Child(Base):
            svc: _Svc = sp.Singleton(_Svc, logger=Base.provider.logger)

        fake = _Logger()
        with Base.set_overrides(logger=fake):
            assert Child.svc.logger is fake
