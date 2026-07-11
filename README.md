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
`Dependency`, `Selector`, `Provider`, `Container` (nested container),
`ContextLocalContainer` / `ThreadLocalContainer` / `TestLocalContainer` (scoped
subcontainers), and the test-scoped `TestContextSingleton`.

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

## Scoped subcontainers (async / thread / test isolation)

The root is a single global composition root, so `set_overrides` on it mutates
shared state — not safe when tests, async tasks or threads run concurrently in one
process. Scope a **subcontainer** instead: each scope gets its own isolated copy
of the nested container's providers (a `providers.deepcopy`, so overriding the
copy's `cfg` flows to the copy's `db`), and the root is never touched.

```python
class Inner(StaticDeclarativeContainer):
    cfg: Config = sp.Singleton(load_config)
    db: Database = sp.Singleton(Database, config=cfg)

class Root(StaticDeclarativeContainer):
    inner: type[Inner] = sp.TestLocalContainer(Inner)

# a test overrides ITS copy — isolated from the root and from other tests
Root.inner.set_overrides(cfg=fake)   # typed + checked, like any set_overrides
db = Root.inner.db                   # resolves against this scope's copy
```

- **`TestLocalContainer(Inner)`** — reset per test by the bundled plugin (like
  `TestContextSingleton`); each test gets a fresh copy.
- **`ThreadLocalContainer(Inner)`** — a copy per thread (`threading.local`).
- **`ContextLocalContainer(Inner)`** — a copy per `contextvars` context. A fresh
  thread gets its own; async **tasks** copy their parent's context, so sibling
  tasks share a lazily-created copy — enter a fresh context (or use
  `TestLocalContainer`) when you need strict per-task isolation.

Reads and `set_overrides` are typed as the nested container (autocomplete +
typo-checked), exactly like `Container`.

## Test-scoped providers

`TestContextSingleton` holds a value for the duration of one test and is reset
between tests. Reset is driven by an explicit hook, per test framework:

**Run under pytest** — auto-cleaned. The bundled plugin (auto-registered on
install) calls `reset_all_test_contexts()` after every test; nothing to wire up.
This covers `unittest.TestCase` tests too, since pytest can run them — if your
test runner is `pytest`, you get auto-clean regardless of how the tests are
written:

```python
class Services(StaticDeclarativeContainer):
    driver: Driver = sp.TestContextSingleton(make_driver)

# after each test the plugin resets every container's test-scoped providers
```

To **opt out** of the auto-reset, disable the plugin the standard pytest way —
`pytest -p no:static_dependency_injector`, or in config:

```toml
[tool.pytest.ini_options]
addopts = ["-p", "no:static_dependency_injector"]
```

**Run under the stock `unittest` runner** (`python -m unittest`) — there is no
plugin auto-discovery outside pytest, so register the reset yourself with
`addCleanup`:

```python
class Test(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(Services.reset_test_context)
```

Reset is **per container**: `Services.reset_test_context()` resets only that
container's (own + inherited) `TestContextSingleton` providers — override it to
customise one container without affecting others. `reset_all_test_contexts()`
sweeps every container, routing through each one's `reset_test_context()`.

## Test context (metadata, hooks, session info)

`static_dependency_injector.testing.TestContext` exposes *which* test is running
and per-run session info — framework-neutrally (pytest **and** `unittest`):

```python
from static_dependency_injector.testing import TestContext, CurrentTest, TestInfo

TestContext.is_active()      # True inside a test
TestContext.current          # TestInfo(id, name, module, cls, file, params, markers, framework, raw)
TestContext.current.name     # e.g. "test_login"
TestContext.work_dir         # per-run session info: rootdir / cwd
TestContext.run_id           # unique id for this run
TestContext.started_at       # timezone-aware datetime
```

`TestContext.current` **raises** `NoActiveTestError` outside a test — guard with
`TestContext.is_active()`. Depend on it from a provider with `CurrentTest()`
(resolves to the active `TestInfo` on each access; wrap in `Delegate` for a lazy
`Callable[[], TestInfo]`):

```python
class Services(StaticDeclarativeContainer):
    test: TestInfo = CurrentTest()

Services.test.name           # the running test's name
```

React to test boundaries with hooks (usable as decorators). `on_exit` fires
*before* test-scoped providers are reset:

```python
@TestContext.on_enter
def seed(info: TestInfo) -> None:
    ...   # e.g. tag resources with info.id
```

**pytest**: activation is automatic (the bundled plugin sets the context in setup,
clears it in teardown). **unittest** (stock runner): wrap the test with
`TestContext.scope(self)`:

```python
class Test(unittest.TestCase):
    def setUp(self) -> None:
        cm = TestContext.scope(self)
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)   # also resets test-scoped providers
```

The current test is stored in a `contextvars.ContextVar`, so it composes with
`ContextLocalSingleton` / `TestContextSingleton`. A thread spawned inside a test
does **not** inherit it automatically — capture the context and run within it:

```python
ctx = contextvars.copy_context()
threading.Thread(target=lambda: ctx.run(work)).start()   # sees TestContext.current
```

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

**Redeclaring a dependency does not rewire inherited dependents.** A plain
subclass that redeclares only a *dependency* leaves an inherited *dependent* wired
to the original provider (this matches `dependency_injector`'s plain subclassing).
Use `@copy` to rewire them — it mirrors `dependency_injector`'s `@containers.copy`:

```python
from static_dependency_injector.containers import copy

class Base(StaticDeclarativeContainer):
    config: Config = sp.Singleton(Config, "postgres://")
    db: Database = sp.Singleton(Database, config=config)

class Plain(Base):
    config: Config = sp.Singleton(Config, "sqlite://")
Plain.db.config.url        # "postgres://" — dependent NOT rewired

@copy(Base)
class Testing(Base):
    config: Config = sp.Singleton(Config, "sqlite://")
Testing.db.config.url      # "sqlite://" — @copy rewired db to Testing.config
```

Direct attribute assignment stays rejected (use `set_overrides`); `@copy` opens a
brief, scoped bypass only for the rewiring it performs.

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

## On-demand resolvers (`Delegate`)

Wiring a sibling by name injects its **resolved value**, captured once. When a
consumer must re-resolve the *current* value on each use — e.g. it depends on a
`TestContextSingleton` that is reset between tests — wire it with `Delegate`, which
yields a `Callable[[], T]`:

```python
class Core(StaticDeclarativeContainer):
    logger: Logger = sp.TestContextSingleton(Logger)
    waiter: Waiter = sp.ContextLocalSingleton(Waiter, logger_resolver=sp.Delegate(logger))
    #                                                 ^ typed Callable[[], Logger]
```

```python
class Waiter:
    def __init__(self, logger_resolver: Callable[[], Logger]) -> None:
        self._logger = logger_resolver          # keep the callable
    def wait(self) -> None:
        self._logger().info("waiting…")         # resolves the current logger per use
```

`Delegate` wraps dependency-injector's delegation. You can't write `logger.provider`
directly here: inside the body `logger` is typed as `Logger` (its resolved type), so
`.provider` is a type error — `Delegate(logger)` bridges that, staying clean under
ty/mypy/pyright.

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