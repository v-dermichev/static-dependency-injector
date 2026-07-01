"""A provider declared without a type annotation warns at class creation, since
typed overrides (``set_overrides``) can only see annotated fields. Inheritance is
respected: a name annotated anywhere in the MRO does not warn."""
from __future__ import annotations

import warnings
from collections.abc import Callable

import pytest

from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import (
    StaticDeclarativeContainer,
    UnannotatedProviderWarning,
)


def _warnings_for(build: Callable[[], None]) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        build()
    return [
        str(w.message)
        for w in caught
        if issubclass(w.category, UnannotatedProviderWarning)
    ]


class TestUnannotatedProviderWarning:
    def test_unannotated_provider_warns(self) -> None:
        def build() -> None:
            class Services(StaticDeclarativeContainer):
                logger = sp.Singleton(str)  # no annotation

        msgs = _warnings_for(build)
        assert len(msgs) == 1
        assert "Services.logger" in msgs[0]
        assert "annotation" in msgs[0]

    def test_annotated_provider_does_not_warn(self) -> None:
        def build() -> None:
            class Services(StaticDeclarativeContainer):
                logger: str = sp.Singleton(str)

        assert _warnings_for(build) == []

    def test_inherited_annotation_suppresses_warning(self) -> None:
        class Base(StaticDeclarativeContainer):
            logger: str = sp.Singleton(str)

        def build() -> None:
            class Child(Base):
                logger = sp.Singleton(str)  # redeclared, annotation inherited
                extra = sp.Singleton(str)  # new + unannotated -> warns

        msgs = _warnings_for(build)
        assert len(msgs) == 1
        assert "Child.extra" in msgs[0]

    def test_warning_is_filterable_to_error(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", UnannotatedProviderWarning)
            with pytest.raises(UnannotatedProviderWarning):

                class Services(StaticDeclarativeContainer):
                    logger = sp.Singleton(str)
