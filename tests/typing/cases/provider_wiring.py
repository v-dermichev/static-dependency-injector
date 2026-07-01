"""Wiring a subclass provider from an inherited provider via ``Base.provider.x``
is autocompleted and typo-checked - clean under ty/mypy/pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Logger:
    pass


class Svc:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger


class Base(StaticDeclarativeContainer):
    logger: Logger = sp.Singleton(Logger)


class Child(Base):
    # `logger` is out of scope in this body; reference the inherited provider.
    # `Base.provider.logger` autocompletes and is typo-checked (typed as the
    # container field); at runtime it is the provider object, wired lazily.
    svc: Svc = sp.Singleton(Svc, logger=Base.provider.logger)
