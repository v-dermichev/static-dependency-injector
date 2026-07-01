# static-dependency-injector

[![PyPI](https://img.shields.io/pypi/v/static-dependency-injector)](https://pypi.org/project/static-dependency-injector/)
[![License](https://img.shields.io/pypi/l/static-dependency-injector)](https://github.com/v-dermichev/static-dependency-injector/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-v--dermichev%2Fstatic--dependency--injector-blue?logo=github)](https://github.com/v-dermichev/static-dependency-injector)

Static, lazily-resolved declarative DI containers built on top of
[`dependency-injector`](https://github.com/ets-labs/python-dependency-injector).

Declare providers as annotated class attributes and read them back as resolved
**values** straight from the container class — no instance, no `()` call.
Overrides are **fully type-checked**: the provider names and value types are
verified (and autocompleted) by ty, mypy and pyright.

```python
from static_dependency_injector import static_providers as sp
from static_dependency_injector.containers import StaticDeclarativeContainer


class Services(StaticDeclarativeContainer):
    config: Config = sp.Singleton(load_config)
    db: Database = sp.Singleton(Database, config=config)


db = Services.db                                # resolved Database (lazy, cached)

with Services.set_overrides(db=fake_db):        # scoped — auto-restored on exit
    ...
Services.set_overrides(db=fake_db)              # or permanent
Services.set_overrides(db=sp.Factory(FakeDb))   # a provider works too (fresh each resolve)

Services.set_overrides(dbb=fake_db)             # ❌ unknown provider (type error)
Services.set_overrides(db=123)                  # ❌ wrong value type (type error)
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
- **Fully typed** — reads resolve to the dependency's type, and `set_overrides`
  checks provider names *and* value types under ty, mypy and pyright (Pylance),
  with autocompletion on the real fields.
- **Lazy & cached** — keeps `dependency-injector`'s resolution and per-provider
  caching semantics; nothing is built until first access.
- **Test-friendly** — `set_overrides` (scoped context manager or permanent) for
  per-test overrides, plus `TestContextSingleton` auto-reset via a bundled
  pytest plugin.
- **Thin** — a typed wrapper over `dependency-injector`; no vendoring, no magic
  beyond the container metaclass.

## Providers

Typed wrappers over `dependency-injector` providers (`static_providers`):

`Factory`, `Singleton`, `ThreadSafeSingleton`, `ThreadLocalSingleton`,
`ContextLocalSingleton`, `Callable`, `Coroutine`, `Object`, `Resource`,
`Dependency`, `Selector`, `Provider`, `Container` (nested container), and the
test-scoped `TestContextSingleton`.

Each is generic in its resolved type, so `Services.db` reads back as the
dependency's type.

## Nested containers

Nest a static container with `Container`; reads chain through it, and overriding
the sub-container flows through:

```python
class Inner(StaticDeclarativeContainer):
    db: Database = sp.Singleton(Database)

class Outer(StaticDeclarativeContainer):
    inner: type[Inner] = sp.Container(Inner)

db = Outer.inner.db                 # resolved Database (typed)
with Inner.set_overrides(db=fake):  # reflected through Outer.inner.db
    ...
```

## Test-scoped providers

`TestContextSingleton` holds a value for the duration of one test and is reset
between tests. Reset is driven by an explicit hook, per test framework:

**Run under pytest** — auto-cleaned. The bundled plugin (auto-registered on
install) calls `reset_test_context()` after every test; nothing to wire up. This
covers `unittest.TestCase` tests too, since pytest can run them — if your test
runner is `pytest`, you get auto-clean regardless of how the tests are written:

```python
class Services(StaticDeclarativeContainer):
    driver: Driver = sp.TestContextSingleton(make_driver)

# after each test the plugin calls Services.reset_test_context() for you
```

**Run under the stock `unittest` runner** (`python -m unittest`) — there is no
plugin auto-discovery outside pytest, so register the reset yourself with
`addCleanup`:

```python
class Test(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(Services.reset_test_context)
```

You can also reset manually anywhere: `Services.reset_test_context()`.

## Subclassing & whole-container override

Subclass a container to inherit its providers, and redeclare any to replace them:

```python
class Base(StaticDeclarativeContainer):
    db: Database = sp.Singleton(Database)

class Testing(Base):
    db: Database = sp.Singleton(FakeDatabase)   # replaces Base.db for Testing
    extra: Clock = sp.Singleton(Clock)          # adds a provider

Testing.set_overrides(db=other, extra=frozen)   # typed over inherited + own
```

Override a whole container's providers by name with another container's, undone
with `reset_override` (both reflected in reads):

```python
Base.override(FakeContainer)   # Base.db now resolves FakeContainer.db
Base.reset_override()
```

## Wiring across inheritance

Within one container body you wire by the provider's bare name (`db=config`). In a
**subclass** body that name is out of scope, and `Base.db` would resolve to a
*value*, not the provider. Use `Base.provider.db` to get the provider object —
it's typed as the container, so field names (inherited included) **autocomplete**
and typos are **compile-time errors** under ty/mypy/pyright, while at runtime it's
the lazy provider:

```python
class Base(StaticDeclarativeContainer):
    config: Config = sp.Singleton(load_config)

class Child(Base):
    # `config` is out of scope here; reference the inherited provider:
    service: Service = sp.Singleton(Service, config=Base.provider.config)

Base.provider.confg   # ❌ typo — compile-time error
```

`Container.provider.x` returns the provider (for wiring); `Container.x` returns
the resolved value (for reading). For a **dynamic** name, use the underlying
`Container.providers[name]` (dependency-injector's provider dict).

**Why name the base explicitly?** There is no self-reference inside a class body:
while the body runs the class does not exist yet, and no type checker models "the
class being defined" as a value — the class name, `__class__`, and
dependency-injector's `providers.Self` / `__self__` are all undefined there, at
type-check and at runtime. So reference the base by name.

If something genuinely needs *the container itself*, remember a static container
is just a class — import it and use it directly (`from app.services import
Services; Services.db`); you don't need `providers.Self` for that (it exists for
the dynamic-container case). The only reason to reach for a self-reference is a
**circular import** between a container and a component that annotates it — solve
that with an `if TYPE_CHECKING:` guarded (type-only) import, not a runtime
self-reference.

## Type checking

Reads resolve to the field's type, and `set_overrides` is fully checked under
**ty**, **mypy** and **pyright** (Pylance) — unknown provider names and wrong
value types are compile-time errors, verified by a test matrix that runs all
three. This requires an **annotation** on each provider (`db: Db = Singleton(Db)`)
so the checker knows the field type — like a dataclass or a Pydantic model,
annotations are also inherited, so a subclass sees its bases' fields (and reads /
overrides them with the right types). A provider declared **without** an
annotation still resolves at runtime, but is invisible to `set_overrides`; to
catch that, an `UnannotatedProviderWarning` is emitted at class-creation naming
the provider (filter or escalate it via the standard `warnings` machinery).
Direct attribute assignment (`Services.db = …`) is rejected at runtime — use
`set_overrides`.

## Compatibility with `dependency-injector`

The static, class-level model keeps most of `dependency-injector`'s API, but a
few pieces are intentionally different.

**Preserved:**

- Introspection — `providers`, `cls_providers`, `inherited_providers`,
  `traverse()`, `dependencies`.
- Overriding — `override(other)` / `reset_override()` / `reset_last_overriding()`
  and the `overridden` tuple, plus the `@containers.override(Container)`
  decorator; all reflected in reads.
- Lazy resolution and per-provider caching semantics.

**Deliberately different (because there is no container instance):**

- **Reads return values, not providers** — `Services.db` is the resolved
  `Database`, so `Services.db()` and provider methods like
  `Services.db.override(...)` do not apply. Override with `set_overrides` / the
  container-level `override`; if you need the *provider* object (to wire another
  provider with it), use `Services.provider.db` — typed and autocompleted (see
  [Wiring across inheritance](#wiring-across-inheritance)) — or the untyped
  `Services.providers["db"]`.
- **Instantiation is repurposed** — `Services(db=fake)` applies value overrides
  and returns a restoring handle (usable as a `with` block); it does not build a
  container instance.
- **Direct provider assignment** (`Services.db = provider`) is rejected — use
  `set_overrides`.
- **`init_resources()` / `shutdown_resources()`** are deprecated and raise:
  they are instance-level and meaningless here. A `Resource` still initializes on
  first access, but its post-`yield` teardown is not driven — use `Resource` for
  init-only setup, or manage teardown yourself.

## Notes & limitations

Because containers are resolved at the **class level** (no container instance),
**overrides** go through `set_overrides` (scoped `with …:` restores on exit; a
bare call is permanent), or `override(other_container)` for a whole-container
swap. Both are reflected in reads and cleared by `reset_override`.

`set_overrides` takes either a **value** or a **provider** — mirroring
dependency-injector's `override()`. A value is pinned as-is; a provider keeps its
own semantics, so `set_overrides(db=sp.Factory(FakeDb))` yields a fresh instance
on each resolve (and `sp.Singleton(FakeDb)` a shared one), which is handy for
scoped test overrides. This holds for the scoped form too: the override — value
or provider — is restored when the `with` block exits.

## Requirements

- Python 3.12+ (uses PEP 695 generics)
- `dependency-injector >= 4.49.1`

## License

MIT. Uses `dependency-injector` (BSD-3-Clause) as a runtime dependency; none of
its source is vendored.