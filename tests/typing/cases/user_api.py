"""A realistic user code path - declaring a wired container, reading services,
and overriding them in a test - type-checks clean in ty, mypy and pyright. This
is the API users are pointed at; none of it needs a suppression comment."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Config:
    def __init__(self, url: str) -> None:
        self.url = url


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


class Services(StaticDeclarativeContainer):
    config = sp.Singleton(Config, "postgres://")
    db = sp.Singleton(Database, config=config)


# reads resolve to the service types
cfg: Config = Services.config
database: Database = Services.db
url: str = Services.db.config.url

# override in a test and restore - all typed, no ignores
Services.set_overrides(db=Database(Config("sqlite://")))
Services.clear_overrides("db")
Services.clear_overrides()
Services.reset_test_context()
