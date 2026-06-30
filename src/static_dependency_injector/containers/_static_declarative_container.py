from dependency_injector import containers

from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
)


class StaticDeclarativeContainer(
    containers.DeclarativeContainer,
    metaclass=StaticDeclarativeContainerMeta,
):
    """Base class for static, lazily-resolved DI containers.

    Subclass it and declare providers as class attributes; read them back as
    resolved values via the class (``MyServices.db``). Override per test with
    ``MyServices.db = fake`` and reset with ``del MyServices.db``.
    """
