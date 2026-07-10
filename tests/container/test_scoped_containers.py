"""Scoped subcontainers: each thread / context / test gets an isolated copy of a
nested container's providers, so overriding a scope never touches the root or
other scopes."""
from __future__ import annotations

import contextvars
import threading

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class _Inner(StaticDeclarativeContainer):
    cfg: str = sp.Singleton(lambda: "real")
    db: str = sp.Singleton(lambda cfg: f"db({cfg})", cfg=cfg)


class _Box(StaticDeclarativeContainer):
    sing: object = sp.Singleton(object)  # one instance per scope copy
    fac: object = sp.Factory(object)  # a fresh instance on every access


class TestScopedReadsAndOverrides:
    def test_reads_resolve_and_override_is_isolated_from_root(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.ContextLocalContainer(_Inner)

        assert Root.inner.cfg == "real"
        Root.inner.set_overrides(cfg="fake")
        assert Root.inner.cfg == "fake"
        assert _Inner.cfg == "real"  # root untouched
        Root.inner.reset_override()

    def test_override_flows_through_wiring_in_the_copy(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.ContextLocalContainer(_Inner)

        # override cfg before db is resolved -> the copy's db wires to the copy's cfg
        Root.inner.set_overrides(cfg="fake")
        assert Root.inner.db == "db(fake)"
        assert _Inner.db == "db(real)"  # root's db unchanged

    def test_scoped_with_block_auto_restores(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.ContextLocalContainer(_Inner)

        with Root.inner.set_overrides(cfg="scoped"):
            assert Root.inner.cfg == "scoped"
        assert Root.inner.cfg == "real"


class TestThreadLocalContainer:
    def test_each_thread_isolated(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.ThreadLocalContainer(_Inner)

        seen: dict[str, str] = {}

        def worker(tag: str) -> None:
            Root.inner.set_overrides(cfg=tag)
            seen[tag] = Root.inner.db

        threads = [threading.Thread(target=worker, args=(t,)) for t in ("A", "B")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert seen["A"] == "db(A)"
        assert seen["B"] == "db(B)"
        assert Root.inner.db == "db(real)"  # main thread / root untouched


class TestContextLocalContainer:
    def test_separate_contexts_isolated(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.ContextLocalContainer(_Inner)

        def in_context(tag: str) -> str:
            Root.inner.set_overrides(cfg=tag)
            return Root.inner.db

        r1 = contextvars.copy_context().run(in_context, "one")
        r2 = contextvars.copy_context().run(in_context, "two")
        assert r1 == "db(one)"
        assert r2 == "db(two)"
        assert _Inner.db == "db(real)"  # root untouched


class TestTestLocalContainer:
    def test_reset_test_context_discards_the_copy(self) -> None:
        class Root(StaticDeclarativeContainer):
            inner: type[_Inner] = sp.TestLocalContainer(_Inner)

        Root.inner.set_overrides(cfg="from-a-test")
        assert Root.inner.cfg == "from-a-test"
        Root.reset_test_context()  # end of test
        assert Root.inner.cfg == "real"  # fresh copy for the next test
        assert _Inner.cfg == "real"


class TestScopedInstanceIdentity:
    """Guard the instance-identity contract (not just resolved values): each scope
    holds its own copy, so a scoped `Singleton` is one instance within a scope and
    a distinct one in another; a scoped `Factory` is always fresh."""

    def test_context_local_singleton_stable_within_distinct_across(self) -> None:
        class Root(StaticDeclarativeContainer):
            box: type[_Box] = sp.ContextLocalContainer(_Box)

        def within() -> tuple[object, object]:
            return Root.box.sing, Root.box.sing

        a1, a2 = contextvars.copy_context().run(within)
        b1, b2 = contextvars.copy_context().run(within)
        assert a1 is a2 and b1 is b2  # stable within a context
        assert a1 is not b1  # distinct instance in another context

    def test_context_local_factory_fresh_within_a_context(self) -> None:
        class Root(StaticDeclarativeContainer):
            box: type[_Box] = sp.ContextLocalContainer(_Box)

        def within() -> tuple[object, object]:
            return Root.box.fac, Root.box.fac

        f1, f2 = contextvars.copy_context().run(within)
        assert f1 is not f2  # Factory: a new instance on every access

    def test_thread_local_singleton_distinct_across_threads(self) -> None:
        class Root(StaticDeclarativeContainer):
            box: type[_Box] = sp.ThreadLocalContainer(_Box)

        main = Root.box.sing
        assert Root.box.sing is main  # stable within the main thread
        seen: dict[str, object] = {}

        def worker() -> None:
            seen["sing"] = Root.box.sing

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert seen["sing"] is not main  # a distinct instance in another thread
