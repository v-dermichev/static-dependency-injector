# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/); while pre-1.0, minor versions may
include breaking changes.

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

[0.2.0]: https://github.com/v-dermichev/static-dependency-injector/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/v-dermichev/static-dependency-injector/releases/tag/v0.1.0
