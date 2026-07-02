"""Scoped subcontainer providers.

Nest a container so each *scope* (thread / contextvars context / test) gets its
own isolated copy of the subcontainer's providers. The root stays a single global
composition root; a test, request or thread overrides its *own* copy, never the
root's shared state.

The copy is a ``providers.deepcopy`` of the subcontainer's providers, so the copy
is wired to itself - overriding the copy's ``cfg`` flows to the copy's ``db`` -
and the root is untouched.

``ContextLocalContainer`` (contextvars) isolates per thread and per fresh
context; async *tasks* copy their parent's context, so sibling tasks share a
lazily-created copy - enter a fresh scope (or use ``TestLocalContainer``, reset
per test) when you need per-task isolation. ``ThreadLocalContainer``
(``threading.local``) isolates per thread. ``TestLocalContainer`` is context-local
and discarded per test by the bundled plugin.
"""
import contextvars
import threading
from typing import Any, cast, override

from dependency_injector import providers


class _ScopedOverrideHandle:
    """Like the container's override handle, but over a scope's copied providers:
    removes on exit exactly the overrides it added (by identity)."""

    def __init__(self, providers_map: dict[str, Any], added: dict[str, Any]) -> None:
        self._providers = providers_map
        self._added = added

    def __enter__(self) -> "_ScopedOverrideHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        for name, mine in self._added.items():
            provider = self._providers[name]
            remaining = [o for o in provider.overridden if o is not mine]
            if len(remaining) != len(provider.overridden):
                provider.reset_override()
                for other in remaining:
                    provider.override(other)


class _ScopedView:
    """Read/override handle over one scope's copied providers. ``view.x`` resolves
    the value; ``view.set_overrides(...)`` / ``view.reset_override()`` act on the
    copy only. Typed (via the factory lie) as the subcontainer class, so field
    names autocomplete and ``set_overrides`` is checked."""

    def __init__(self, providers_map: dict[str, Any]) -> None:
        object.__setattr__(self, "_providers", providers_map)

    def __getattr__(self, name: str) -> Any:
        providers_map = object.__getattribute__(self, "_providers")
        if name in providers_map:
            return providers_map[name]()
        raise AttributeError(name)

    def set_overrides(self, **overrides: Any) -> _ScopedOverrideHandle:
        providers_map = object.__getattribute__(self, "_providers")
        added: dict[str, Any] = {}
        for name, value in overrides.items():
            if name not in providers_map:
                raise TypeError(f"scoped container has no provider {name!r}")
            override = value if isinstance(value, providers.Provider) else providers.Object(value)
            providers_map[name].override(override)
            added[name] = override
        return _ScopedOverrideHandle(providers_map, added)

    def reset_override(self) -> None:
        for provider in object.__getattribute__(self, "_providers").values():
            provider.reset_override()


class _ScopedContainer(providers.Provider[Any]):
    """Base: a subcontainer provider whose read (``Root.inner``) returns a
    per-scope :class:`_ScopedView` over an isolated copy of the subcontainer's
    providers. Subclasses supply the per-scope storage."""

    def __init__(self, container_cls: Any) -> None:
        self._static_cls = container_cls
        super().__init__()

    def _fresh(self) -> dict[str, Any]:
        return providers.deepcopy(dict(self._static_cls.providers))

    def _map(self) -> dict[str, Any]:
        raise NotImplementedError

    def __get__(self, _obj: object, _owner: type | None = None) -> _ScopedView:
        return _ScopedView(self._map())

    def _provide(self, args: Any, kwargs: Any) -> _ScopedView:
        return _ScopedView(self._map())


class _ThreadLocalContainer(_ScopedContainer):
    def __init__(self, container_cls: Any) -> None:
        super().__init__(container_cls)
        self._local = threading.local()

    @override
    def _map(self) -> dict[str, Any]:
        existing = getattr(self._local, "map", None)
        if existing is None:
            existing = self._fresh()
            self._local.map = existing
        return existing


class _ContextLocalContainer(_ScopedContainer):
    def __init__(self, container_cls: Any) -> None:
        super().__init__(container_cls)
        self._var: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
            f"scoped:{container_cls.__name__}",
        )

    @override
    def _map(self) -> dict[str, Any]:
        try:
            return self._var.get()
        except LookupError:
            fresh = self._fresh()
            self._var.set(fresh)
            return fresh

    def reset_scope(self) -> None:
        """Discard this context's copy (next access rebuilds a fresh one)."""
        self._var.set(self._fresh())


class _TestLocalContainer(_ContextLocalContainer):
    """Context-local, and discarded per test by the bundled pytest plugin."""


def ThreadLocalContainer[C](container_cls: type[C], /) -> type[C]:  # noqa: N802
    """Nest ``container_cls`` with a per-thread isolated copy of its providers."""
    return cast(type[C], _ThreadLocalContainer(container_cls))


def ContextLocalContainer[C](container_cls: type[C], /) -> type[C]:  # noqa: N802
    """Nest ``container_cls`` with a per-context (contextvars) isolated copy."""
    return cast(type[C], _ContextLocalContainer(container_cls))


def TestLocalContainer[C](container_cls: type[C], /) -> type[C]:  # noqa: N802
    """Nest ``container_cls`` with an isolated copy that is reset per test."""
    return cast(type[C], _TestLocalContainer(container_cls))
