"""Overriding with an unknown name or a wrong value type is rejected statically."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    pass


class Services(StaticDeclarativeContainer):
    db: Db = sp.Singleton(Db)


Services.set_overrides(db=123)       # wrong value type
Services.set_overrides(nope=Db())     # unknown provider name
