"""TestContext class-properties, session info, and the CurrentTest provider are
well-typed (clean in ty/mypy/pyright)."""
from datetime import datetime
from pathlib import Path

from static_dependency_injector.containers import StaticDeclarativeContainer
from static_dependency_injector.testing import CurrentTest, TestContext, TestInfo

# class-level attribute access, correctly typed
name: str = TestContext.current.name
markers: frozenset[str] = TestContext.current.markers
work_dir: Path = TestContext.work_dir
run_id: str = TestContext.run_id
started_at: datetime = TestContext.started_at
active: bool = TestContext.is_active()

# the current test as a provider, read back as its resolved type
class Services(StaticDeclarativeContainer):
    test: TestInfo = CurrentTest()

who: str = Services.test.name
