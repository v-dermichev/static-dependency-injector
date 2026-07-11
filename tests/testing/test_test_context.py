"""TestContext: current-test metadata + session info under the bundled pytest
plugin, the unittest ``scope()`` integration, the ``CurrentTest`` provider, and
enter/exit hooks."""
from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from typing import override

import pytest

from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.testing import (
    CurrentTest,
    NoActiveTestError,
    TestContext,
    TestInfo,
)


class _Case(unittest.TestCase):
    __test__ = False  # helper, not collected

    def test_demo(self) -> None: ...


class TestPytestActivation:
    def test_current_reflects_the_running_test(self) -> None:
        assert TestContext.is_active()
        info = TestContext.current
        assert info.framework == "pytest"
        assert info.name == "test_current_reflects_the_running_test"
        assert info.id.endswith("test_current_reflects_the_running_test")
        assert info.cls == "TestPytestActivation"
        assert info.module is not None and info.module.endswith("test_test_context")
        assert info.file is not None and info.file.endswith("test_test_context.py")

    @pytest.mark.slow
    def test_markers_are_captured(self) -> None:
        assert "slow" in TestContext.current.markers

    @pytest.mark.parametrize("n", [1, 2])
    def test_params_are_captured(self, n: int) -> None:
        assert TestContext.current.params == {"n": n}

    def test_current_raises_when_inactive(self) -> None:
        token = TestContext._current.set(None)  # simulate "outside a test"
        try:
            assert not TestContext.is_active()
            with pytest.raises(NoActiveTestError):
                _ = TestContext.current
        finally:
            TestContext._current.reset(token)


class TestSessionInfo:
    def test_fields_present_and_stable(self) -> None:
        assert isinstance(TestContext.work_dir, Path)
        assert isinstance(TestContext.run_id, str) and TestContext.run_id
        assert isinstance(TestContext.started_at, datetime)
        assert TestContext.started_at.tzinfo is not None  # timezone-aware
        assert TestContext.run_id == TestContext.run_id  # one id per run


class TestCurrentTestProvider:
    def test_provider_resolves_the_active_test(self) -> None:
        class Svc(StaticDeclarativeContainer):
            t: TestInfo = CurrentTest()

        assert Svc.t is TestContext.current
        assert Svc.t.name == "test_provider_resolves_the_active_test"


class TestHooks:
    def test_enter_and_exit_fire_around_a_scope(self) -> None:
        events: list[tuple[str, str]] = []
        enter = TestContext.on_enter(lambda i: events.append(("enter", i.name)))
        leave = TestContext.on_exit(lambda i: events.append(("exit", i.name)))
        try:
            with TestContext.scope(_Case("test_demo")):
                pass
        finally:
            TestContext._on_enter.remove(enter)
            TestContext._on_exit.remove(leave)
        assert events == [("enter", "test_demo"), ("exit", "test_demo")]

    def test_hook_exception_never_propagates(self) -> None:
        def boom(_i: TestInfo) -> None:
            raise ValueError("nope")

        hook = TestContext.on_enter(boom)
        try:
            with TestContext.scope(_Case("test_demo")):
                pass  # must not raise despite the failing hook
        finally:
            TestContext._on_enter.remove(hook)


class TestUnittestScope:
    def test_scope_activates_and_restores(self) -> None:
        outer = TestContext.current  # the running pytest test
        with TestContext.scope(_Case("test_demo")) as info:
            assert info.framework == "unittest"
            assert info.name == "test_demo"
            assert info.id.endswith("test_demo")
            assert TestContext.current is info
        assert TestContext.current is outer  # restored on exit

    def test_setup_teardown_pattern_runs_green(self) -> None:
        class Case(unittest.TestCase):
            @override
            def setUp(self) -> None:
                cm = TestContext.scope(self)
                cm.__enter__()
                self.addCleanup(cm.__exit__, None, None, None)

            def test_sees_context(self) -> None:
                assert TestContext.current.framework == "unittest"
                assert TestContext.current.name == "test_sees_context"

        suite = unittest.TestLoader().loadTestsFromTestCase(Case)
        result = unittest.TextTestRunner(verbosity=0).run(suite)
        assert result.wasSuccessful()
        assert TestContext.current.framework == "pytest"  # pytest test active again
