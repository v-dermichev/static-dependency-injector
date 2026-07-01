"""Inherited providers are resolved (read at the child) and overridable with the
right types - the typed surface that also drives editor autocompletion. Clean
under ty/mypy/pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    def query(self) -> int:
        return 1


class Base(StaticDeclarativeContainer):
    db: Db = sp.Singleton(Db)
    name: str = sp.Object("base")


class Child(Base):
    count: int = sp.Object(3)      # own provider
    name = sp.Object("child")      # redeclared without annotation -> inherits `str`


# inherited providers resolve to their declared types when read via the subclass
d: Db = Child.db
n: int = Child.db.query()
s: str = Child.name
c: int = Child.count

# set_overrides on the subclass accepts inherited + own fields, typed
Child.set_overrides(db=Db(), name="override", count=9)
