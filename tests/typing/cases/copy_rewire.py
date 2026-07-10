"""``@copy`` rewires a redeclared dependency into inherited dependents and stays
well-typed - reads still resolve to the field types (clean in ty/mypy/pyright)."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer, copy


class Config:
    def __init__(self, url: str) -> None:
        self.url = url


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


class Base(StaticDeclarativeContainer):
    config: Config = sp.Singleton(Config, "postgres://")
    db: Database = sp.Singleton(Database, config=config)


@copy(Base)
class Testing(Base):
    config: Config = sp.Singleton(Config, "sqlite://")   # rewired into Testing.db


# reads still resolve to the annotated field types
cfg: Config = Testing.config
database: Database = Testing.db
url: str = Testing.db.config.url
