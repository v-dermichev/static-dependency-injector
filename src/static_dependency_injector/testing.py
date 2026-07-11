"""Framework-neutral test context: read the current test's metadata and per-run
session info from inside providers or test code, register enter/exit hooks, and
integrate with either pytest (auto, via the bundled plugin) or unittest (opt-in,
via :meth:`TestContext.scope`).

``TestContext.current`` returns a :class:`TestInfo` for the active test (raising
outside one - guard with :meth:`TestContext.is_active`); ``TestContext.work_dir``
/ ``run_id`` / ``started_at`` expose per-run session info. ``CurrentTest()`` wraps
``TestContext.current`` as a provider so a factory can depend on it.

The current test is stored in a :class:`contextvars.ContextVar`, so it composes
with ``ContextLocalSingleton`` / ``TestContextSingleton``. A thread spawned inside
a test does *not* inherit it automatically; capture the context and run within it::

    ctx = contextvars.copy_context()
    threading.Thread(target=lambda: ctx.run(work)).start()  # sees TestContext.current
"""
from __future__ import annotations

import contextvars
import inspect
import unittest
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Literal

Framework = Literal["pytest", "unittest"]
Hook = Callable[["TestInfo"], None]


class NoActiveTestError(RuntimeError):
    """Raised by ``TestContext.current`` when no test is active."""


@dataclass(frozen=True, slots=True)
class TestInfo:
    """Neutral metadata for one test, built from a pytest item or a unittest case."""

    __test__: ClassVar[bool] = False  # not a pytest test class (Test-prefixed name)

    id: str  # item.nodeid / TestCase.id() - the unique, path-like identifier
    name: str  # the test function / method name
    module: str | None
    cls: str | None  # enclosing class qualname, if class-based
    file: str | None
    params: Mapping[str, Any] | None  # pytest parametrization; None for unittest
    markers: frozenset[str]  # pytest marker names; empty for unittest
    framework: Framework
    raw: Any = field(repr=False, compare=False)  # the underlying item / TestCase


@dataclass(frozen=True, slots=True)
class SessionInfo:
    """Per-run info, set once at session start (or lazily on first access)."""

    work_dir: Path
    run_id: str
    started_at: datetime


class _TestContextMeta(type):
    """Metaclass exposing ``TestContext.current`` / ``work_dir`` / ``run_id`` /
    ``started_at`` as class-level attributes (class properties)."""

    @property
    def current(cls: type[TestContext]) -> TestInfo:  # noqa: N805
        info = cls._current.get()
        if info is None:
            raise NoActiveTestError(
                "TestContext.current: no active test. Guard with TestContext.is_active(), "
                "or activate one via the bundled pytest plugin or TestContext.scope().",
            )
        return info

    @property
    def work_dir(cls: type[TestContext]) -> Path:  # noqa: N805
        return cls._ensure_session().work_dir

    @property
    def run_id(cls: type[TestContext]) -> str:  # noqa: N805
        return cls._ensure_session().run_id

    @property
    def started_at(cls: type[TestContext]) -> datetime:  # noqa: N805
        return cls._ensure_session().started_at


class TestContext(metaclass=_TestContextMeta):
    """Namespace/manager for the active test and per-run session info.

    Read ``TestContext.current`` for the active :class:`TestInfo`,
    ``TestContext.is_active()`` to check first, and ``TestContext.work_dir`` /
    ``run_id`` / ``started_at`` for session info. Register hooks with
    :meth:`on_enter` / :meth:`on_exit`. pytest activation is automatic (bundled
    plugin); for unittest wrap the test in :meth:`scope`.
    """

    __test__: ClassVar[bool] = False  # not a pytest test class (Test-prefixed name)

    _current: ClassVar[contextvars.ContextVar[TestInfo | None]] = contextvars.ContextVar(
        "static_di_current_test",
        default=None,
    )
    _session: ClassVar[SessionInfo | None] = None
    _on_enter: ClassVar[list[Hook]] = []
    _on_exit: ClassVar[list[Hook]] = []

    @classmethod
    def is_active(cls) -> bool:
        """Whether a test is currently active (``current`` is safe to read)."""
        return cls._current.get() is not None

    @classmethod
    def on_enter(cls, hook: Hook) -> Hook:
        """Register a callback run when a test becomes active (usable as a
        decorator). Hook exceptions are swallowed so they never fail the run."""
        cls._on_enter.append(hook)
        return hook

    @classmethod
    def on_exit(cls, hook: Hook) -> Hook:
        """Register a callback run when a test ends, *before* test-scoped providers
        are reset (usable as a decorator). Hook exceptions are swallowed."""
        cls._on_exit.append(hook)
        return hook

    @classmethod
    @contextmanager
    def scope(cls, case_or_item: Any) -> Iterator[TestInfo]:
        """Delimit a test as the active one (unittest / manual integration).

        ``case_or_item`` is a unittest ``TestCase``, a pytest item, or a
        :class:`TestInfo`. On exit it fires ``on_exit`` hooks and resets
        test-scoped providers - so it marks a full per-test boundary::

            def setUp(self):
                cm = TestContext.scope(self)
                cm.__enter__()
                self.addCleanup(cm.__exit__, None, None, None)
        """
        info = cls._adapt(case_or_item)
        token = cls._current.set(info)
        cls._fire(cls._on_enter, info)
        try:
            yield info
        finally:
            cls._fire(cls._on_exit, info)
            cls._current.reset(token)
            cls._reset_providers()

    # --- session -----------------------------------------------------------

    @classmethod
    def configure_session(
        cls,
        *,
        work_dir: Path | str | None = None,
        run_id: str | None = None,
        started_at: datetime | None = None,
    ) -> SessionInfo:
        """Set per-run session info (the pytest plugin calls this at startup with
        the rootdir). Missing fields default to cwd / a fresh id / now."""
        cls._session = SessionInfo(
            work_dir=Path(work_dir) if work_dir is not None else Path.cwd(),
            run_id=run_id or uuid.uuid4().hex,
            started_at=started_at or datetime.now(timezone.utc),
        )
        return cls._session

    @classmethod
    def _ensure_session(cls) -> SessionInfo:
        if cls._session is None:
            return cls.configure_session()
        return cls._session

    # --- adapters ----------------------------------------------------------

    @staticmethod
    def from_pytest_item(item: Any) -> TestInfo:
        module = getattr(item, "module", None)
        klass = getattr(item, "cls", None)
        callspec = getattr(item, "callspec", None)
        path = getattr(item, "path", None)
        return TestInfo(
            id=item.nodeid,
            name=getattr(item, "originalname", None) or item.name,
            module=getattr(module, "__name__", None),
            cls=getattr(klass, "__qualname__", None),
            file=str(path) if path is not None else None,
            params=dict(callspec.params) if callspec is not None else None,
            markers=frozenset(mark.name for mark in item.iter_markers()),
            framework="pytest",
            raw=item,
        )

    @staticmethod
    def from_unittest_case(case: unittest.TestCase) -> TestInfo:
        klass = type(case)
        try:
            file: str | None = inspect.getfile(klass)
        except (TypeError, OSError):
            file = None
        return TestInfo(
            id=case.id(),
            name=getattr(case, "_testMethodName", "") or "",
            module=klass.__module__,
            cls=klass.__qualname__,
            file=file,
            params=None,
            markers=frozenset(),
            framework="unittest",
            raw=case,
        )

    # --- internals ---------------------------------------------------------

    @classmethod
    def _adapt(cls, obj: Any) -> TestInfo:
        if isinstance(obj, TestInfo):
            return obj
        if isinstance(obj, unittest.TestCase):
            return cls.from_unittest_case(obj)
        if hasattr(obj, "nodeid"):
            return cls.from_pytest_item(obj)
        raise TypeError(f"TestContext.scope: cannot build TestInfo from {obj!r}")

    @classmethod
    def _enter(cls, info: TestInfo) -> None:
        """Activate ``info`` (used by the pytest plugin's setup hook)."""
        cls._current.set(info)
        cls._fire(cls._on_enter, info)

    @classmethod
    def _exit(cls) -> None:
        """Fire ``on_exit`` hooks, clear the active test, reset providers (used by
        the pytest plugin's teardown hook). pytest's runtest protocol is flat, so a
        plain clear (not a token restore) is correct here."""
        info = cls._current.get()
        if info is not None:
            cls._fire(cls._on_exit, info)
        cls._current.set(None)
        cls._reset_providers()

    @staticmethod
    def _fire(hooks: list[Hook], info: TestInfo) -> None:
        for hook in list(hooks):
            try:
                hook(info)
            except Exception:  # noqa: BLE001 - a hook must never fail the test run
                pass

    @staticmethod
    def _reset_providers() -> None:
        # Lazy import avoids a static_providers -> testing -> containers cycle at
        # import time, and keeps a reset failure from breaking teardown.
        try:
            from static_dependency_injector.containers import StaticDeclarativeContainer

            StaticDeclarativeContainer.reset_all_test_contexts()
        except Exception:  # noqa: BLE001
            pass


def CurrentTest() -> TestInfo:  # noqa: N802 - a provider factory, like `sp.Singleton`
    """Provider resolving to :attr:`TestContext.current` on each access, so a
    factory can depend on the active test (``t: TestInfo = CurrentTest()``). Raises
    outside a test; wrap with ``Delegate`` for a lazy ``Callable[[], TestInfo]``."""
    from static_dependency_injector import static_providers as sp

    return sp.Callable(lambda: TestContext.current)
