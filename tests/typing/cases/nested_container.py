"""Nested static containers read cleanly: ``Outer.inner.x`` resolves to the
sub-provider's type under ty/mypy/pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    def query(self) -> int:
        return 1


class Inner(StaticDeclarativeContainer):
    db: Db = sp.Singleton(Db)


class Outer(StaticDeclarativeContainer):
    inner: type[Inner] = sp.Container(Inner)


d: Db = Outer.inner.db
n: int = Outer.inner.db.query()
