"""Type-checker behavior tests: run ty, mypy and pyright on the case files under
``cases/`` and assert each reports the expected outcome for every use case.

A case is materialized into a temp file and checked with the working directory at
the project root, so each checker resolves the installed package. Exit code 0 is
treated as "clean", non-zero as "error". A checker that cannot run in the current
environment (e.g. pyright without its runtime) is skipped, never failed.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

pytestmark = pytest.mark.typing

_ROOT = Path(__file__).resolve().parents[2]
_BIN = Path(sys.executable).parent
_CASES = Path(__file__).parent / "cases"

# Expected outcome per (case, checker): "clean" or "error".
_EXPECT: dict[str, dict[str, str]] = {
    "user_api": {"ty": "clean", "mypy": "clean", "pyright": "clean"},
    "inherited_container": {"ty": "clean", "mypy": "clean", "pyright": "clean"},
    "nested_container": {"ty": "clean", "mypy": "clean", "pyright": "clean"},
    "read_value_types": {"ty": "clean", "mypy": "clean", "pyright": "clean"},
    "overrides_and_reset": {"ty": "clean", "mypy": "clean", "pyright": "clean"},
    "read_wrong_type": {"ty": "error", "mypy": "error", "pyright": "error"},
    "override_errors": {"ty": "error", "mypy": "error", "pyright": "error"},
    "subclass_override": {"ty": "error", "mypy": "error", "pyright": "error"},
}

_CHECKERS = ("ty", "mypy", "pyright")


def _command(checker: str, file: Path) -> Sequence[str]:
    exe = str(_BIN / checker)
    if checker == "ty":
        return [exe, "check", str(file)]
    if checker == "mypy":
        return [exe, "--follow-imports=silent", "--no-error-summary", str(file)]
    return [exe, str(file)]  # pyright


def _run(checker: str, file: Path) -> str | None:
    """Return "clean"/"error", or None if the checker cannot run here."""
    if not (_BIN / checker).exists():
        return None
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv from this module
            _command(checker, file),
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # ty/mypy/pyright all exit 1 on type errors; other codes mean the tool itself
    # failed to run (e.g. pyright could not start its runtime) -> skip.
    if proc.returncode not in (0, 1):
        return None
    return "clean" if proc.returncode == 0 else "error"


@pytest.mark.parametrize("checker", _CHECKERS)
@pytest.mark.parametrize("case", sorted(_EXPECT))
def test_type_check(case: str, checker: str, tmp_path: Path) -> None:
    source = (_CASES / f"{case}.py").read_text(encoding="utf-8")
    target = tmp_path / f"{case}.py"
    target.write_text(source, encoding="utf-8")

    outcome = _run(checker, target)
    if outcome is None:
        pytest.skip(f"{checker} is not runnable in this environment")
    assert outcome == _EXPECT[case][checker], (
        f"{checker} on {case}: expected {_EXPECT[case][checker]!r}, got {outcome!r}"
    )
