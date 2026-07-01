"""A realistic user path - wired container, typed reads, typed overrides - clean
in ty, mypy and pyright."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Config:
    def __init__(self, url: str) -> None:
        self.url = url


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


class Services(StaticDeclarativeContainer):
    config: Config = sp.Singleton(Config, "postgres://")
    db: Database = sp.Singleton(Database, config=config)


cfg: Config = Services.config
url: str = Services.db.config.url
Services.set_overrides(db=Database(Config("sqlite://")))
with Services.set_overrides(db=Database(Config("x"))):
    pass
Services.reset_test_context()
