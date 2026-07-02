"""End-to-end: the bundled plugin auto-registers (``pytest11`` entry point) and
resets ``TestContextSingleton`` between tests with no manual wiring."""
from __future__ import annotations

import pytest


class TestPluginAutoRegistration:
    def test_resets_test_scoped_between_tests(self, pytester: pytest.Pytester) -> None:
        pytester.makepyfile(
            """
            import itertools

            from static_dependency_injector import static_providers as sp
            from static_dependency_injector.containers import StaticDeclarativeContainer

            _counter = itertools.count()


            class Services(StaticDeclarativeContainer):
                scoped: int = sp.TestContextSingleton(lambda: next(_counter))


            _seen = []


            def test_first():
                v = Services.scoped
                assert Services.scoped == v
                _seen.append(v)


            def test_second():
                _seen.append(Services.scoped)
                assert _seen[0] != _seen[1]   # plugin reset between tests
            """,
        )
        result = pytester.runpytest_inprocess("-p", "no:cacheprovider")
        result.assert_outcomes(passed=2)

    def test_opt_out_disables_reset(self, pytester: pytest.Pytester) -> None:
        pytester.makepyfile(
            """
            import itertools

            from static_dependency_injector import static_providers as sp
            from static_dependency_injector.containers import StaticDeclarativeContainer

            _counter = itertools.count()


            class Services(StaticDeclarativeContainer):
                scoped: int = sp.TestContextSingleton(lambda: next(_counter))


            _seen = []


            def test_first():
                _seen.append(Services.scoped)


            def test_second():
                _seen.append(Services.scoped)
                assert _seen[0] == _seen[1]   # plugin disabled -> no reset, same value
            """,
        )
        # standard pytest opt-out for the bundled plugin
        result = pytester.runpytest_inprocess("-p", "no:cacheprovider", "-p", "no:static_dependency_injector")
        result.assert_outcomes(passed=2)
