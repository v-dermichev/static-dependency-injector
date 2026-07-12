"""pytest plugin: expose the current test via ``TestContext`` and reset
``TestContextSingleton`` providers after each test.

Auto-registered through the ``pytest11`` entry point, so any suite that installs
this package gets, for free: per-run session info, ``TestContext.current`` during
each test (plus ``on_enter`` / ``on_exit`` hooks), and per-test reset of
test-scoped providers - replacing manual ``provider.reset()`` in teardown.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def pytest_configure(config: Any) -> None:
    # Record per-run session info (work_dir from the rootdir). Never fail startup.
    try:
        from static_dependency_injector.testing import TestContext

        TestContext.configure_session(work_dir=Path(str(config.rootpath)))
    except Exception:  # noqa: BLE001
        pass


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: Any) -> None:
    # Activate the current test so TestContext.current / CurrentTest() resolve.
    # `tryfirst`: enter BEFORE any fixture setup, so fixtures can read CurrentTest().
    try:
        from static_dependency_injector.testing import TestContext

        TestContext._enter(TestContext.from_pytest_item(item))
    except Exception:  # noqa: BLE001
        pass


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: Any) -> None:
    # Fire on_exit hooks, clear the active test, and reset test-scoped providers.
    # Lazy import keeps plugin load cheap; failures here must never fail the run.
    #
    # `trylast`: reset AFTER all fixture finalizers. Fixture teardowns commonly
    # touch a test-scoped provider to release its resource (e.g. `svc = X.driver`
    # in setup, `X.driver.quit()` in teardown). If we reset first, that access
    # rebuilds a fresh instance mid-teardown - for a real resource (WebDriver /
    # Appium session) that means a new session and a hang. Resetting last lets
    # teardowns see the same instance they set up.
    try:
        from static_dependency_injector.testing import TestContext

        TestContext._exit()
    except Exception:  # noqa: BLE001
        try:
            from static_dependency_injector.containers import StaticDeclarativeContainer

            StaticDeclarativeContainer.reset_all_test_contexts()
        except Exception:  # noqa: BLE001
            pass
