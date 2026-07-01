"""A typo on ``Container.provider.<name>`` is a compile-time error (the getter
is typed as the container class), under ty/mypy/pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Logger:
    pass


class Base(StaticDeclarativeContainer):
    logger: Logger = sp.Singleton(Logger)


bad = Base.provider.loggr  # ERROR: no such provider
