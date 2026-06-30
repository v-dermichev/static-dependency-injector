from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, ClassVar, cast

from dependency_injector import providers

from static_dependency_injector.containers._container_config_dict import ContainerConfigDict

if TYPE_CHECKING:
    # The shipped stubs don't export the declarative metaclass; for the checker
    # we only need to know it is a metaclass (a ``type``). At runtime we subclass
    # the real one so containers behave like dependency_injector's.
    _DeclarativeContainerMeta = type
else:
    from dependency_injector.containers import (
        DeclarativeContainerMetaClass as _DeclarativeContainerMeta,
    )


class StaticDeclarativeContainerMeta(_DeclarativeContainerMeta):
    """Lifts declared providers onto a per-class metaclass as resolved
    properties, and registers them under the container's ``name``.
    """

    _REGISTRY: ClassVar[dict[str, dict[str, providers.Provider[Any]]]] = {}
    _REGISTRY_LOCK: ClassVar[threading.RLock] = threading.RLock()

    @staticmethod
    def _resolved_property(name: str, attr: str) -> property:
        """Build a class property that resolves provider ``name``/``attr`` lazily."""
        registry = StaticDeclarativeContainerMeta._REGISTRY

        def fget(_cls: Any) -> Any:
            return registry[name][attr]()

        def fset(cls: Any, value: Any) -> None:
            provider = registry[name][attr]
            hook = getattr(provider, "_static_di_on_set", None)
            if hook is not None:
                value = hook(cls, value)
            provider.override(providers.Object(value))

        def fdel(_cls: Any) -> None:
            registry[name][attr].reset_override()

        return property(fget, fset, fdel)

    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> StaticDeclarativeContainerMeta:
        own = {attr: value for attr, value in namespace.items() if isinstance(value, providers.Provider)}
        if own:
            config: ContainerConfigDict = namespace.get("container_config", {})
            module = namespace.get("__module__", "")
            qualname = namespace.get("__qualname__", cls_name)
            name = config.get("name") or (f"{module}.{qualname}" if module else qualname)
            with mcs._REGISTRY_LOCK:
                bucket = mcs._REGISTRY.setdefault(name, {})
                for attr, provider in own.items():
                    bucket.setdefault(attr, provider)  # first writer under a name wins
            props = {attr: mcs._resolved_property(name, attr) for attr in own}
            mcs = cast(
                "type[StaticDeclarativeContainerMeta]",
                type(f"_{cls_name}Meta", (mcs,), props),  # ty:ignore[unsupported-dynamic-base]
            )
        return super().__new__(mcs, cls_name, bases, namespace, **kwargs)

    @classmethod
    def reset_test_context(cls) -> None:
        """Reset every test-scoped provider (``TestContextSingleton``) across all
        registered containers, so the next test gets fresh instances.

        The bundled pytest plugin calls this on each test teardown, so a manual
        ``provider.reset()`` in a test ``finally`` is no longer needed. Also
        callable directly: ``MyServices.reset_test_context()``.
        """
        with cls._REGISTRY_LOCK:
            test_scoped = [
                provider
                for bucket in cls._REGISTRY.values()
                for provider in bucket.values()
                if getattr(provider, "_static_di_test_scoped", False)
            ]
        for provider in test_scoped:
            reset = getattr(provider, "reset", None)
            if callable(reset):
                reset()
