from collections.abc import Callable
from typing import Any

from dependency_injector import containers as _di_containers

from static_dependency_injector.containers._static_declarative_container import StaticDeclarativeContainer
from static_dependency_injector.containers._static_declarative_container_meta import (
    UnannotatedProviderWarning,
)


def copy[C: StaticDeclarativeContainer](base: Any) -> Callable[[type[C]], type[C]]:
    """Decorator mirroring dependency_injector's ``@containers.copy(base)``.

    On a subclass it rewires redeclared dependencies into their inherited
    dependents. A plain subclass keeps dependents wired to the *original*
    providers::

        class Base(StaticDeclarativeContainer):
            config: Config = Singleton(Config)
            db: Database = Singleton(Database, config=config)

        @copy(Base)
        class Testing(Base):
            config: Config = Singleton(FakeConfig)   # db now resolves FakeConfig

    Direct attribute assignment stays rejected (use ``set_overrides``); this
    decorator opens a brief, scoped bypass only for the rewiring it performs.
    """
    di_decorator = _di_containers.copy(base)

    def decorator(new: type[C]) -> type[C]:
        setattr(new, "_sdi_rewiring", True)  # metaclass guard reads this flag
        try:
            return di_decorator(new)
        finally:
            setattr(new, "_sdi_rewiring", False)

    return decorator


__all__ = ("StaticDeclarativeContainer", "UnannotatedProviderWarning", "copy")
