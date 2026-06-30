from typing import TypedDict


class ContainerConfigDict(TypedDict, total=False):
    """Per-container configuration.

    ``name`` defaults to the fully-qualified class name (``module.QualName``).
    Two container classes sharing a ``name`` share one set of provider
    bindings (first writer under a name wins; overrides are visible to every
    class registered under that name).
    """

    name: str
