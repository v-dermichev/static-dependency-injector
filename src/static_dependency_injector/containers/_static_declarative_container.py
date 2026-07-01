from typing import Any, Self, dataclass_transform
from typing import override as _override

from dependency_injector import containers
from typing_extensions import deprecated

from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
)
from static_dependency_injector.static_providers._container_providers import _TEST_SCOPED

# init_resources()/shutdown_resources() act on a container *instance*; a static,
# class-level container has none, so they are deprecated and raise this.
_INSTANCE_ONLY = (
    "{name}() operates on a container instance; a static (class-level) container "
    "has no instance and does not drive resource lifecycle. Providers initialise "
    "lazily on first access - manage any teardown yourself."
)


class _SetOverrides:
    """Descriptor: ``Container.set_overrides`` returns the container type, so the
    call reuses the ``dataclass_transform``-synthesized (typed) constructor."""

    def __get__[C](self, _obj: object, owner: type[C]) -> type[C]:
        return owner


@dataclass_transform(kw_only_default=True)
class StaticDeclarativeContainer(
    containers.DeclarativeContainer,
    metaclass=StaticDeclarativeContainerMeta,
):
    """Base for static, lazily-resolved, fully-typed DI containers.

    Declare providers as annotated class attributes; read them back as resolved
    values via the class. Override them - names and value types checked by the
    type checker - with ``set_overrides``:

    ```python
    class Services(StaticDeclarativeContainer):
        config: Config = Singleton(Config)
        db: Database = Singleton(Database, config=config)

    db = Services.db                              # resolved Database
    with Services.set_overrides(db=fake_db):      # scoped, auto-restored on exit
        ...
    Services.set_overrides(db=fake_db)            # or permanent
    ```
    """

    set_overrides = _SetOverrides()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    @classmethod
    @_override
    def override(cls, overriding: Any) -> None:
        """Override this container's providers with another container's, by name
        (whole-container override) - reflected in reads. Undo with
        :meth:`reset_override` or :meth:`reset_last_overriding`. Providers not
        present here are ignored.
        """
        super().override(overriding)  # record container-level overriding state
        for name, provider in overriding.providers.items():
            if name in cls.providers:
                cls.providers[name].override(provider)  # reflect in reads

    @classmethod
    @_override
    def reset_override(cls) -> None:
        """Clear all overrides (from :meth:`override` or ``set_overrides``), and
        the container-level overriding state."""
        super().reset_override()

    @classmethod
    @_override
    @deprecated(
        "init_resources() is instance-level and has no meaning for a static "
        "container; providers initialise lazily on first access.",
    )
    def init_resources(cls, *_args: object, **_kwargs: object) -> Any:
        """Deprecated: unsupported for static containers (raises)."""
        raise NotImplementedError(_INSTANCE_ONLY.format(name="init_resources"))

    @classmethod
    @_override
    @deprecated(
        "shutdown_resources() is instance-level and has no meaning for a static "
        "container; manage any teardown yourself.",
    )
    def shutdown_resources(cls, *_args: object, **_kwargs: object) -> Any:
        """Deprecated: unsupported for static containers (raises)."""
        raise NotImplementedError(_INSTANCE_ONLY.format(name="shutdown_resources"))

    @classmethod
    def reset_test_context(cls) -> None:
        """Reset every ``TestContextSingleton`` provider, so the next test gets
        fresh instances. Called by the bundled pytest plugin after each test."""
        for provider in _TEST_SCOPED:
            provider.reset()
