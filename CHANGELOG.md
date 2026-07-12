# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/); while pre-1.0, minor versions may
include breaking changes.

## [0.3.9] - 2026-07-12

### Fixed
- The bundled pytest plugin now resets test-scoped (`TestContextSingleton`)
  providers **after** fixture finalizers, not before (`trylast` on
  `pytest_runtest_teardown`; and `tryfirst` on `pytest_runtest_setup` so the
  context is entered before fixtures too). A fixture that captures a test-scoped
  resource in setup and releases it in teardown — the common `svc = X.driver` /
  `svc.quit()` pattern — previously hit the reset *between* the two: re-reading
  the provider in teardown rebuilt a fresh instance, which for a real resource
  (a WebDriver / Appium session) meant a brand-new session and a hang. The reset
  is now deferred until all finalizers have run, so teardowns see the same
  instance they set up.

## [0.3.8] - 2026-07-10

### Added
- `static_dependency_injector.testing.TestContext` — framework-neutral (pytest and
  `unittest`) access to the current test and per-run session info: `current`
  (a `TestInfo` with id / name / module / cls / file / params / markers / framework
  / raw; raises `NoActiveTestError` outside a test — guard with `is_active()`),
  `work_dir` / `run_id` / `started_at`, and `on_enter` / `on_exit` hooks.
- `CurrentTest()` — a provider resolving to `TestContext.current`, so a factory can
  depend on the active test (`test: TestInfo = CurrentTest()`).
- The bundled pytest plugin now activates the context per test (and captures the
  session at startup) in addition to resetting test-scoped providers. For unittest,
  wrap the test with `TestContext.scope(self)`.

## [0.3.7] - 2026-07-10

### Fixed
- `copy` rewiring now shares the redeclared provider *by identity*: a redeclared
  `Singleton` resolves to the same instance the rewired dependent sees, instead of
  a distinct copy with an equal value. dependency_injector's own `copy` deep-copies
  the subclass's providers a second time, leaving the attribute and the dependent
  as two objects (two caches); the wrapper now deep-copies the inherited providers
  once with a memo onto the redeclared originals and keeps those originals as-is.

## [0.3.6] - 2026-07-10

### Added
- `Delegate(provider)` — wire a sibling provider as an on-demand resolver, typed
  `Callable[[], T]`. Inside a container body a provider is typed as its resolved
  value (`logger: Logger`), so dependency_injector's own delegation
  (`logger.provider`) does not type-check. `Delegate(logger)` closes that gap: the
  consumer receives a callable that resolves the *current* value on each call —
  for a dependency that must re-resolve (e.g. across a `TestContextSingleton`
  reset) instead of capturing one instance. Typed clean under ty, mypy and pyright.

## [0.3.5] - 2026-07-10

### Added
- `ContextLocalContainer` / `ThreadLocalContainer` / `TestLocalContainer` — scoped
  subcontainer providers. Each scope (contextvars context / thread / test) gets an
  isolated `providers.deepcopy` of the nested container, so a test, request or
  thread overrides its *own* copy while the root composition root is untouched.
  Reads and `set_overrides` are typed as the nested container.
  `TestLocalContainer` is discarded per test by the bundled plugin.
- `reset_all_test_contexts()` — resets test-scoped providers for every container,
  routing through each container's (possibly overridden) `reset_test_context()`.
  The bundled pytest plugin calls this after each test.
- `copy` — a decorator mirroring `dependency_injector`'s `@containers.copy`. On a
  subclass it rewires redeclared dependencies into their inherited dependents (a
  plain subclass keeps dependents wired to the original providers). The assignment
  guard stays strict — direct provider assignment is still rejected — because the
  decorator opens only a brief, scoped bypass for the rewiring it performs. Typed
  clean under ty, mypy and pyright.

### Changed
- `reset_test_context()` is now **scoped to the container it's called on** (its
  own + inherited `TestContextSingleton` providers), instead of resetting every
  test-scoped provider process-wide. Overriding it on one container no longer
  affects others.

### Fixed
- Scoped `set_overrides` now removes on exit *exactly* the override it added
  (matched by identity), instead of popping whichever override is on top. Nested
  scopes exiting out of order, and a bare (permanent) `set_overrides` interleaved
  inside a `with` block, no longer leave a stale override behind or drop the wrong
  one.
- Removed `ty` from the runtime dependencies (it was listed by mistake; `ty` is a
  dev-only type checker).

## [0.3.2] - 2026-07-01

### Changed
- `set_overrides` now mirrors dependency_injector's `override()`: a **provider**
  argument (e.g. `set_overrides(logger=Factory(...))`) is used as-is (a `Factory`
  yields a fresh instance each resolve), while a plain **value** is wrapped in
  `Object` as before. Previously a provider was wrapped in `Object` too, so it
  leaked the provider object instead of resolving through it.

### Added
- `UnannotatedProviderWarning` — emitted at class creation for a provider
  declared without a type annotation (which typed `set_overrides` can't see).
  Annotations are inherited across the MRO, so redeclaring an already-annotated
  provider in a subclass does not warn.
- `Container.provider.<name>` — a typed accessor for the underlying provider
  object, for wiring a provider from another one across a class boundary (e.g. an
  inherited provider whose bare name is out of scope in the subclass body). Field
  names autocomplete and typos are compile-time errors under ty/mypy/pyright;
  `Container.<name>` still returns the resolved value. For a dynamic name, the
  existing `Container.providers[name]` dict returns the same provider object.

## [0.3.1] - 2026-07-01

### Added
- `override(other_container)` / `reset_override()` apply a whole-container swap by
  provider name, reflected in reads (dependency_injector's own container override
  did not affect class-level reads). Subclassing inherits and can redeclare
  providers; `set_overrides` on a subclass checks inherited and own fields.
- `Container(SubContainer)` provider for nesting: `inner: type[Inner] =
  Container(Inner)` makes `Outer.inner.x` resolve `Inner.x` (fully typed, and
  sub-container overrides flow through).
- `override()` now also records dependency_injector's container-level overriding
  state, so the inherited `reset_last_overriding()` works and `overridden` is
  populated (previously our override was per-provider only).

### Deprecated
- `init_resources()` / `shutdown_resources()` — instance-level in
  dependency_injector, they have no meaning for a static, class-level container.
  They are marked deprecated (flagged by ty/mypy/pyright) and raise
  `NotImplementedError`; providers still initialise lazily on first access.

### Changed
- `set_overrides` is now **fully type-checked**: provider names *and* value types
  are verified (and autocompleted) by ty, mypy and pyright. Use
  `Services.set_overrides(db=fake)` (permanent) or
  `with Services.set_overrides(db=fake): ...` (scoped, auto-restored on exit).
- Providers are now **factory functions** and each field needs an **annotation**:
  `db: Database = Singleton(Database, config=config)` — this is what lets the
  checker verify overrides. Wiring (`config=config`) is unchanged.
- Direct attribute assignment (`Services.db = ...`) is rejected at runtime; use
  `set_overrides`.

### Removed
- `clear_overrides` — a scoped `with Services.set_overrides(...)` restores
  automatically; `ContainerConfigDict` / shared-by-name bindings.

## [0.2.0]

### Added
- `StaticDeclarativeContainer.set_overrides(**values)` and
  `clear_overrides(*names)` classmethods — the typed, cross-checker-clean way to
  override providers (e.g. in tests), validating provider names.

### Changed
- Direct attribute-assignment override (`Container.attr = value`) is no longer
  part of the typed API. The provider wrappers no longer expose `__set__` /
  `__delete__`, so ty, mypy and pyright uniformly reject it — use
  `set_overrides` / `clear_overrides` instead. Runtime resolution and reads are
  unchanged.

## [0.1.0]

### Added
- Initial release: `StaticDeclarativeContainer` + metaclass (providers declared
  as class attributes resolve to values via the class; shared-by-name bindings).
- `static_providers`: typed wrappers (`Factory`, `Singleton`, thread/context
  scopes, `Callable`, `Coroutine`, `Object`, `Resource`, `Dependency`,
  `Selector`, `Provider`) plus the test-scoped `TestContextSingleton`.
- Bundled pytest plugin (auto-registered) that resets `TestContextSingleton`
  providers after each test.

[0.3.9]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.2...v0.3.5
[0.3.2]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.2.0...v0.3.1
[0.2.0]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/v-dermichev/static-dependency-injector/releases/tag/v0.1.0
