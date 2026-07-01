"""The typed override API - names and value types checked, scoped and permanent -
plus reset_test_context, all clean in ty/mypy/pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    pass


class Services(StaticDeclarativeContainer):
    db: Db = sp.Singleton(Db)
    count: int = sp.Object(0)


Services.set_overrides(db=Db(), count=5)   # multiple, correct types
Services.set_overrides(db=Db())            # subset
with Services.set_overrides(db=Db()):      # scoped - auto-restores on exit
    pass
Services.reset_test_context()
