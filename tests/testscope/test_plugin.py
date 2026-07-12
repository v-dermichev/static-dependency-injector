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

    def test_reset_runs_after_fixture_finalizers(self, pytester: pytest.Pytester) -> None:
        """Reset must happen AFTER fixture teardowns, not before.

        Fixtures commonly capture a test-scoped provider in setup and release it
        in teardown (``svc = X.driver`` / ``svc.quit()``). If the plugin reset
        ran first, re-reading the provider in teardown would rebuild a fresh
        instance mid-teardown - for a real resource (WebDriver / Appium session)
        that means a brand-new session and a hang.
        """
        pytester.makepyfile(
            """
            import itertools

            import pytest

            from static_dependency_injector import static_providers as sp
            from static_dependency_injector.containers import StaticDeclarativeContainer

            _counter = itertools.count()


            class Services(StaticDeclarativeContainer):
                scoped: int = sp.TestContextSingleton(lambda: next(_counter))


            @pytest.fixture(autouse=True)
            def fx():
                built = Services.scoped        # setup: build the instance
                yield
                # teardown: must see the SAME instance (reset is deferred to
                # after fixture finalizers). A rebuild here would be a new value.
                assert Services.scoped == built, (
                    "test-scoped provider was reset BEFORE the fixture teardown "
                    "(re-access rebuilt it)"
                )


            def test_ok():
                pass
            """,
        )
        result = pytester.runpytest_inprocess("-p", "no:cacheprovider")
        result.assert_outcomes(passed=1)

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
