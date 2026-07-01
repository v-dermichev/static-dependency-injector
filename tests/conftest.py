"""Isolate the process-wide test-scoped provider registry between tests."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from static_dependency_injector.static_providers import _container_providers as _cp

pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def _isolated_test_scoped() -> Iterator[None]:
    saved = set(_cp._TEST_SCOPED)
    _cp._TEST_SCOPED.clear()
    try:
        yield
    finally:
        _cp._TEST_SCOPED.clear()
        _cp._TEST_SCOPED.update(saved)
