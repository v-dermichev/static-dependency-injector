# static-dependency-injector

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


db = Services.db          # resolved Database instance (lazy, cached)
Services.db = fake_db     # override (e.g. in a test)
del Services.db           # reset the override
```

Providers stay lazy: the underlying callables are not invoked until first access,
and each provider keeps `dependency-injector`'s caching semantics.

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

## Requirements

- Python 3.12+ (uses PEP 695 generics)
- `dependency-injector >= 4.49.1`

## License

MIT. Uses `dependency-injector` (BSD-3-Clause) as a runtime dependency; none of
its source is vendored.