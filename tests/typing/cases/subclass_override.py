"""Overrides on a subclass check inherited + own fields."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Base(StaticDeclarativeContainer):
    a: int = sp.Object(1)


class Child(Base):
    b: str = sp.Object("x")


Child.set_overrides(a=1, b="y")    # OK - inherited + own
Child.set_overrides(a="wrong")      # ERROR wrong type (inherited field)
Child.set_overrides(nope=1)         # ERROR unknown
