"""Reads resolve to the provider's value type ``T`` (clean in ty/mypy/pyright)."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    pass


class Services(StaticDeclarativeContainer):
    singleton_db = sp.Singleton(Db)
    factory_db = sp.Factory(Db)
    text = sp.Object("s")
    number = sp.Callable(lambda: 1)


a: Db = Services.singleton_db
b: Db = Services.factory_db
c: str = Services.text
d: int = Services.number
