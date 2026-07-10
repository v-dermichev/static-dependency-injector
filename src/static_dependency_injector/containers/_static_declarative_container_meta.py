"""Metaclass for static containers.

Under type checking it is a plain ``type`` - so its runtime ``__call__`` does not
shadow the ``dataclass_transform``-synthesized constructor, and
dependency_injector's (un-exported) metaclass is avoided. At runtime it subclasses
``DeclarativeContainerMetaClass`` and repurposes ``Container(**overrides)`` to
apply value-overrides to the class providers, returning a restore handle.
"""
from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any

# Every container class registers here (weak, so test-local containers are GC'd).
# The global test-context reset routes through each container's own
# reset_test_context, so a per-container override is honoured.
_CONTAINERS: weakref.WeakSet[Any] = weakref.WeakSet()


class UnannotatedProviderWarning(UserWarning):
    """A provider was declared without a type annotation, so typed overrides
    (``set_overrides``) cannot recognise it. Annotate it (``name: Type = ...``)
    or filter this category to silence it."""


if TYPE_CHECKING:
    StaticDeclarativeContainerMeta = type
else:
    import warnings

    from dependency_injector import containers, providers

    class _OverrideHandle:
        """Applies the overrides immediately; as a context manager, removes on
        exit *exactly* the overriding providers it added - identified by object
        identity, not "the last one". So nested scopes exiting out of order, and a
        bare (permanent) ``set_overrides`` interleaved inside a ``with`` block,
        each restore correctly instead of popping whichever override happens to be
        on top."""

        def __init__(self, cls: Any, added: dict[str, Any]) -> None:
            self._cls = cls
            self._added = added  # provider name -> the overriding provider we pushed

        def __enter__(self) -> _OverrideHandle:
            return self

        def __exit__(self, *_exc: object) -> None:
            for name, mine in self._added.items():
                provider = self._cls.providers[name]
                remaining = [o for o in provider.overridden if o is not mine]
                if len(remaining) != len(provider.overridden):
                    provider.reset_override()  # then re-apply the survivors in order
                    for other in remaining:
                        provider.override(other)

    class StaticDeclarativeContainerMeta(containers.DeclarativeContainerMetaClass):
        def __init__(cls, *args: Any, **kwargs: Any) -> None:  # noqa: N805
            super().__init__(*args, **kwargs)
            _CONTAINERS.add(cls)
            # A provider needs an annotation somewhere in the MRO to be a typed
            # field (dataclass_transform aggregates fields across bases, like a
            # dataclass); otherwise set_overrides can't see it. Warn per own
            # provider that is annotated nowhere in the hierarchy.
            annotated: set[str] = set()
            for klass in cls.__mro__:
                annotated.update(vars(klass).get("__annotations__", {}))
            for name in cls.cls_providers:
                if name not in annotated:
                    warnings.warn(
                        f"{cls.__name__}.{name} is a provider without a type "
                        f"annotation; typed overrides (set_overrides) won't "
                        f"recognise it. Declare it as `{name}: <Type> = ...`.",
                        UnannotatedProviderWarning,
                        stacklevel=2,
                    )

        def __call__(cls, **overrides: Any) -> _OverrideHandle:  # noqa: N805
            added: dict[str, Any] = {}
            for name, value in overrides.items():
                if name not in cls.providers:
                    raise TypeError(f"{cls.__name__} has no provider {name!r}")
                # Mirror dependency_injector's override(): a provider is used as-is
                # (e.g. Factory -> fresh instance each resolve); a plain value is
                # wrapped in Object.
                override = value if isinstance(value, providers.Provider) else providers.Object(value)
                cls.providers[name].override(override)
                added[name] = override
            return _OverrideHandle(cls, added)

        def __setattr__(cls, name: str, value: Any) -> None:  # noqa: N805
            # `Container.attr = x` would silently clobber the provider; steer to
            # set_overrides (this fires at runtime; type checkers can't see it).
            # The `copy` decorator opens `_sdi_rewiring` briefly to rewire
            # redeclared dependencies into inherited dependents.
            if not cls.__dict__.get("_sdi_rewiring", False):
                try:
                    is_provider = name in cls.providers
                except Exception:  # noqa: BLE001 - providers not ready during creation
                    is_provider = False
                if is_provider:
                    raise AttributeError(f"assign via {cls.__name__}.set_overrides({name}=...)")
            super().__setattr__(name, value)
