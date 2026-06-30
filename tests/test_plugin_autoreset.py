"""End-to-end check that the bundled pytest plugin auto-registers (via its
``pytest11`` entry point) and resets ``TestContextSingleton`` between tests
without any manual reset or conftest wiring."""
from __future__ import annotations

import pytest


def test_plugin_resets_test_scoped_between_tests(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import itertools

        from static_dependency_injector import static_providers as sp
        from static_dependency_injector.containers import StaticDeclarativeContainer

        _counter = itertools.count()


        class Services(StaticDeclarativeContainer):
            scoped = sp.TestContextSingleton(lambda: next(_counter))


        _seen = []


        def test_first():
            v = Services.scoped
            assert Services.scoped == v   # stable within a test
            _seen.append(v)


        def test_second():
            _seen.append(Services.scoped)
            # different instance than test_first -> the plugin reset between tests
            assert _seen[0] != _seen[1]
        """,
    )
    result = pytester.runpytest_inprocess("-p", "no:cacheprovider")
    result.assert_outcomes(passed=2)
