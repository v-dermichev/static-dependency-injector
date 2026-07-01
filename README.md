# static-dependency-injector

[![PyPI](https://img.shields.io/pypi/v/static-dependency-injector)](https://pypi.org/project/static-dependency-injector/)
[![License](https://img.shields.io/pypi/l/static-dependency-injector)](https://github.com/v-dermichev/static-dependency-injector/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-v--dermichev%2Fstatic--dependency--injector-blue?logo=github)](https://github.com/v-dermichev/static-dependency-injector)

Static, lazily-resolved declarative DI containers built on top of
[`dependency-injector`](https://github.com/ets-labs/python-dependency-injector).

Declare providers as class attributes and read them back as resolved **values**
straight from the container class — no instance, no `()` call:

```python
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Services(StaticDeclarativeContainer):
    config = sp.Singleton(load_config)
    db = sp.Singleton(Database, config=config)


db = Services.db                       # resolved Database instance (lazy, cached)
Services.set_overrides(db=fake_db)     # override (e.g. in a test)
Services.clear_overrides("db")         # clear it (or clear_overrides() for all)
```

Providers stay lazy: the underlying callables are not invoked until first access,
and each provider keeps `dependency-injector`'s caching semantics.

## Installation

```bash
pip install static-dependency-injector
# or
uv add static-dependency-injector
```

## Why

- **Read providers as values** — `Services.db` returns the resolved instance, no
  `()` call and no container instance.
- **Fully typed** — reads resolve to the dependency's type, and the override API
  is clean under ty, mypy and pyright (Pylance).
- **Lazy & cached** — keeps `dependency-injector`'s resolution and per-provider
  caching semantics; nothing is built until first access.
- **Test-friendly** — `set_overrides` / `clear_overrides` for per-test overrides,
  plus `TestContextSingleton` auto-reset via a bundled pytest plugin.
- **Thin** — a typed wrapper over `dependency-injector`; no vendoring, no magic
  beyond the container metaclass.

## Providers

Typed wrappers over `dependency-injector` providers (`static_providers`):

`Factory`, `Singleton`, `ThreadSafeSingleton`, `ThreadLocalSingleton`,
`ContextLocalSingleton`, `Callable`, `Coroutine`, `Object`, `Resource`,
`Dependency`, `Selector`, `Provider`, and the test-scoped `TestContextSingleton`.

Each is generic in its resolved type, so `Services.db` reads back as the
dependency's type.

## Test-scoped providers

`TestContextSingleton` is reset automatically after every test by the bundled
pytest plugin (auto-registered on install) — no manual `reset()` in teardown:

```python
class Services(StaticDeclarativeContainer):
    driver = sp.TestContextSingleton(make_driver)

# after each test the plugin calls Services.reset_test_context() for you
```

You can also reset manually: `Services.reset_test_context()`.

## Type checking

Reads resolve to the dependency's type, and the override API type-checks clean
under **ty**, **mypy** and **pyright** (Pylance) — verified by a test matrix that
runs all three. Overriding is done with `set_overrides` / `clear_overrides`;
direct attribute assignment (`Services.db = …`) is intentionally rejected by all
three checkers, so there is one obvious, typed way to override.

## Notes & limitations

Because containers are resolved at the **class level** (no container instance):

- **Overrides** go through `set_overrides` / `clear_overrides`.
  dependency_injector's *container-level* override
  (`Container.override(other_container)`) does **not** affect resolution here -
  reads come from the static registry, not a container instance.
- **`Resource` teardown** is not triggered automatically: a `Resource` provider
  initializes on first access, but its post-`yield` teardown needs a container
  instance / `shutdown_resources()`, which the class-level model does not drive.
  Use `Resource` for init-only setup, or manage teardown yourself.

## Requirements

- Python 3.12+ (uses PEP 695 generics)
- `dependency-injector >= 4.49.1`

## License

MIT. Uses `dependency-injector` (BSD-3-Clause) as a runtime dependency; none of
its source is vendored.