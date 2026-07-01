"""Override classmethods, reset, and ``del`` are well-typed (clean everywhere)."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    pass


class Services(StaticDeclarativeContainer):
    db = sp.Singleton(Db)
    count = sp.Object(0)


Services.set_overrides(db=Db(), count=5)
Services.set_overrides(db=Db())
Services.clear_overrides("db")
Services.clear_overrides()
Services.reset_test_context()
