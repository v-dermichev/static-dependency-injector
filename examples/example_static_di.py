from typing import override

from examples.example_services.counter import Counter
from examples.example_services.http_client_service import HttpClientService
from examples.example_services.logger_service import LoggerService
from examples.example_services.user_provider_service import UserProviderService
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class ExampleStaticDI(StaticDeclarativeContainer):
    logger: LoggerService = sp.TestContextSingleton(LoggerService)
    http_client: HttpClientService = sp.Factory(HttpClientService, logger=logger)
    user_provider: UserProviderService = sp.Singleton(UserProviderService, http_client=http_client, logger=logger)


class ChildWithExtraDependency(ExampleStaticDI):
    provision_count: int = sp.Factory(lambda: Counter.count)
    counter: Counter = sp.Factory(Counter)
    user_provider: UserProviderService = sp.Singleton(
        UserProviderService, logger=ExampleStaticDI.provider.logger, http_client=ExampleStaticDI.provider.http_client
    )


class CustomLogger(LoggerService):
    def __init__(self, key: str):
        self.key = key

    @override
    def log(self, message):
        print(self.key + f": {message}")


class NotSubclassedLogger:
    def log(self):
        print("can't be overriden, unsafe")


class RequiresGlobalAccessibleDeps:
    def lazily_resolved_deps_on_call(self):
        ExampleStaticDI.logger.log("That will use regular logger")

    def overriding_mid_use(self):
        # set_overrides accepts a value or a provider (mirrors di's override):
        # a provider is used as-is, a plain value is wrapped in Object.

        # language=python
        "ExampleStaticDI.set_overrides(logger=NotSubclassedLogger)"

        with ExampleStaticDI.set_overrides(logger=sp.Factory(lambda: CustomLogger("mid_use_overriden"))):
            ExampleStaticDI.logger.log("overriden here")
            # mid_use_overriden: overriden here
        ExampleStaticDI.logger.log("not_anymore")
        # "not anymore"
