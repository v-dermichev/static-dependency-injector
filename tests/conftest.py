"""Isolate the process-wide container registry between tests, so one test's
containers are not swept by another's reset_all_test_contexts()."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from static_dependency_injector.containers import _static_declarative_container_meta as _meta

pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def _isolated_containers() -> Iterator[None]:
    saved = set(_meta._CONTAINERS)  # strong refs keep them alive across the test
    _meta._CONTAINERS.clear()
    try:
        yield
    finally:
        _meta._CONTAINERS.clear()
        for container in saved:
            _meta._CONTAINERS.add(container)
