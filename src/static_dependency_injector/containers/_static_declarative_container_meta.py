"""Metaclass for static containers.

Under type checking it is a plain ``type`` - so its runtime ``__call__`` does not
shadow the ``dataclass_transform``-synthesized constructor, and
dependency_injector's (un-exported) metaclass is avoided. At runtime it subclasses
``DeclarativeContainerMetaClass`` and repurposes ``Container(**overrides)`` to
apply value-overrides to the class providers, returning a restore handle.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    StaticDeclarativeContainerMeta = type
else:
    from dependency_injector import containers, providers

    class _OverrideHandle:
        """Applies the overrides immediately; as a context manager, restores
        them on exit (``with Container.set_overrides(...): ...``)."""

        def __init__(self, cls: Any, names: tuple[str, ...]) -> None:
            self._cls = cls
            self._names = names

        def __enter__(self) -> _OverrideHandle:
            return self

        def __exit__(self, *_exc: object) -> None:
            for name in self._names:
                provider = self._cls.providers[name]
                if provider.overridden:
                    provider.reset_last_overriding()

    class StaticDeclarativeContainerMeta(containers.DeclarativeContainerMetaClass):
        def __call__(cls, **overrides: Any) -> _OverrideHandle:  # noqa: N805
            for name, value in overrides.items():
                if name not in cls.providers:
                    raise TypeError(f"{cls.__name__} has no provider {name!r}")
                cls.providers[name].override(providers.Object(value))
            return _OverrideHandle(cls, tuple(overrides))

        def __setattr__(cls, name: str, value: Any) -> None:  # noqa: N805
            # `Container.attr = x` would silently clobber the provider; steer to
            # set_overrides (this fires at runtime; type checkers can't see it).
            try:
                is_provider = name in cls.providers
            except Exception:  # noqa: BLE001 - providers not ready during creation
                is_provider = False
            if is_provider:
                raise AttributeError(f"assign via {cls.__name__}.set_overrides({name}=...)")
            super().__setattr__(name, value)
