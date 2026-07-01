"""Direct attribute assignment is not part of the typed API: every checker
rejects it (the provider exposes no ``__set__``), steering users to
``set_overrides``. The metaclass still applies the override at runtime, but the
typed surface is uniform across ty / mypy / pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    pass


class Services(StaticDeclarativeContainer):
    db = sp.Singleton(Db)


Services.db = Db()
