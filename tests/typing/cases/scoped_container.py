"""Scoped subcontainers read and override with the nested container's types -
clean under ty/mypy/pyright (like a plain `Container`, but scope-isolated)."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Db:
    def q(self) -> int:
        return 1


class Inner(StaticDeclarativeContainer):
    db: Db = sp.Singleton(Db)


class Root(StaticDeclarativeContainer):
    ctx: type[Inner] = sp.ContextLocalContainer(Inner)
    thread: type[Inner] = sp.ThreadLocalContainer(Inner)
    test: type[Inner] = sp.TestLocalContainer(Inner)


d: Db = Root.ctx.db
n: int = Root.ctx.db.q()
Root.ctx.set_overrides(db=Db())
with Root.thread.set_overrides(db=Db()):
    pass
