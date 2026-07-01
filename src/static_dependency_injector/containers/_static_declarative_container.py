from typing import Any

from dependency_injector import containers

from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
    _ResolvedProperty,
)


class StaticDeclarativeContainer(
    containers.DeclarativeContainer,
    metaclass=StaticDeclarativeContainerMeta,
):
    """Base class for static, lazily-resolved DI containers.

    Subclass it and declare providers as class attributes; read them back as
    resolved values via the class (``MyServices.db``). Replace providers per
    test with :meth:`set_overrides` and restore them with :meth:`clear_overrides`.
    """

    @classmethod
    def _provider_names(cls) -> frozenset[str]:
        """Names of this container's providers (own and inherited)."""
        return frozenset(
            attr
            for klass in type(cls).__mro__
            for attr, value in vars(klass).items()
            if isinstance(value, _ResolvedProperty)
        )

    @classmethod
    def set_overrides(cls, **values: Any) -> None:
        """Override named providers with concrete values until cleared.

        ``MyServices.set_overrides(db=fake_db, clock=frozen)`` swaps each
        provider's resolved value (running its ``on_set`` hook). A subsequent
        ``MyServices.db`` then returns ``fake_db``. Prefer this over attribute
        assignment - it type-checks cleanly.
        """
        unknown = set(values) - cls._provider_names()
        if unknown:
            raise TypeError(f"{cls.__name__} has no provider(s): {sorted(unknown)}")
        for name, value in values.items():
            setattr(cls, name, value)

    @classmethod
    def clear_overrides(cls, *names: str) -> None:
        """Clear provider overrides. With ``names`` clear those; with none,
        clear every provider on this container."""
        valid = cls._provider_names()
        targets = frozenset(names) if names else valid
        unknown = targets - valid
        if unknown:
            raise TypeError(f"{cls.__name__} has no provider(s): {sorted(unknown)}")
        for name in targets:
            delattr(cls, name)
