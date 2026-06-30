"""Isolate the process-wide static-DI registry between tests.

``StaticDeclarativeContainerMeta._REGISTRY`` is process-wide; containers declared
in one test would otherwise leak into the next. This fixture snapshots, clears
for the duration of the test, and restores the original state.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from static_dependency_injector.containers._static_declarative_container_meta import (
    StaticDeclarativeContainerMeta,
)

# Enable the `pytester` fixture for the end-to-end plugin auto-registration test.
pytest_plugins = ["pytester"]


@pytest.fixture(autouse=True)
def _isolated_registry() -> Iterator[None]:
    reg = StaticDeclarativeContainerMeta._REGISTRY
    saved = {name: dict(bucket) for name, bucket in reg.items()}
    reg.clear()
    try:
        yield
    finally:
        reg.clear()
        reg.update(saved)

