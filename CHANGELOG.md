# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/); while pre-1.0, minor versions may
include breaking changes.

## [0.3.2]

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

[0.3.2]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.2.0...v0.3.1
[0.2.0]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/v-dermichev/static-dependency-injector/releases/tag/v0.1.0
