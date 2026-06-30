"""pytest plugin: reset ``TestContextSingleton`` providers after each test.

Auto-registered through the ``pytest11`` entry point, so any test suite that
installs this package gets per-test reset of test-scoped providers for free,
replacing manual ``provider.reset()`` calls in test teardown.
"""
from __future__ import annotations

from typing import Any


def pytest_runtest_teardown(item: Any) -> None:
    # Lazy import keeps plugin load cheap and avoids import-order coupling;
    # failures here must never fail the test run.
    try:
        from static_dependency_injector.containers import StaticDeclarativeContainer

        StaticDeclarativeContainer.reset_test_context()
    except Exception:  # noqa: BLE001
        pass
