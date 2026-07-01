"""Reading a provider into the wrong type is rejected by every checker."""
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Services(StaticDeclarativeContainer):
    count = sp.Object(0)


wrong: str = Services.count  # count resolves to int, not str
