"""`Delegate(sibling)` wires a provider as a typed `Callable[[], T]`, letting a
consumer re-resolve the current value - clean in ty/mypy/pyright."""
from collections.abc import Callable

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Logger:
    def info(self, msg: str) -> None: ...


class Waiter:
    def __init__(self, logger_resolver: Callable[[], Logger]) -> None:
        self._logger = logger_resolver

    def wait(self) -> None:
        self._logger().info("waiting")


class Core(StaticDeclarativeContainer):
    logger: Logger = sp.TestContextSingleton(Logger)
    # `logger` is typed `Logger` here, so `logger.provider` would not type-check;
    # Delegate bridges it to the Callable[[], Logger] the consumer expects.
    waiter: Waiter = sp.ContextLocalSingleton(Waiter, logger_resolver=sp.Delegate(logger))
