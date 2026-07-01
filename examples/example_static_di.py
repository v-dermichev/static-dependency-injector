from pydantic import BaseModel, Field

from examples.example_services.http_client_service import HttpClientService
from examples.example_services.logger_service import LoggerService
from examples.example_services.user_provider_service import UserProviderService
from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.static_providers import Factory, Singleton


class ExampleStaticDI(StaticDeclarativeContainer):
    logger = Singleton(LoggerService)
    http_client = Factory(HttpClientService, logger=logger)
    user_provider = Singleton(UserProviderService, http_client=http_client, logger=logger)


ExampleStaticDI.clear_overrides("http_client")


class M(BaseModel):
    a = Field()
