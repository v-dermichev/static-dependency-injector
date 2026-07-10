from collections.abc import Callable
from typing import Any

from dependency_injector import providers as _providers

from static_dependency_injector.containers._static_declarative_container import StaticDeclarativeContainer
from static_dependency_injector.containers._static_declarative_container_meta import (
    UnannotatedProviderWarning,
)


def copy[C: StaticDeclarativeContainer](base: Any) -> Callable[[type[C]], type[C]]:
    """Decorator mirroring dependency_injector's ``@containers.copy(base)``.

    On a subclass it rewires redeclared dependencies into their inherited
    dependents, *sharing the redeclared provider by identity* - so a redeclared
    ``Singleton`` resolves to the same instance the dependent sees. A plain
    subclass instead keeps dependents wired to the original providers::

        class Base(StaticDeclarativeContainer):
            config: Config = Singleton(Config)
            db: Database = Singleton(Database, config=config)

        @copy(Base)
        class Testing(Base):
            config: Config = Singleton(FakeConfig)   # db now resolves FakeConfig

    Direct attribute assignment stays rejected (use ``set_overrides``); this
    decorator opens a brief, scoped bypass only for the rewiring it performs.

    Unlike dependency_injector's own ``copy``, the rewiring preserves identity:
    that decorator deep-copies the subclass's own providers a second time, so a
    redeclared provider and the dependent rewired to it end up as two objects
    (two ``Singleton`` caches). Here the inherited providers are deep-copied once
    with a memo mapping each base provider to the subclass's redeclared one, and
    the redeclared providers are kept as-is - so the dependent and the attribute
    are the same object.
    """

    def decorator(new: type[C]) -> type[C]:
        own = dict(new.cls_providers)  # providers declared in the subclass body
        base_providers = base.providers
        # map each base provider to the subclass's same-named (redeclared) one, so
        # deepcopy rewires inherited dependents onto the redeclared providers.
        memo = {id(base_providers[name]): prov for name, prov in own.items() if name in base_providers}
        rewired = _providers.deepcopy(base_providers, memo)
        rewired.update(own)  # keep redeclared providers by identity (memo targets)

        setattr(new, "_sdi_rewiring", True)  # metaclass guard reads this flag
        try:
            for name, provider in rewired.items():
                setattr(new, name, provider)
        finally:
            setattr(new, "_sdi_rewiring", False)
        return new

    return decorator


__all__ = ("StaticDeclarativeContainer", "UnannotatedProviderWarning", "copy")
