# Config Providers

Last updated: 2025-12-14

## Summary

- `EnvironmentConfigProvider`: Reads `APERILEX_*` environment variables into an in-memory cache, performs lightweight type coercion, and masks sensitive keys on export.

## EnvironmentConfigProvider

**Location**: `src/infrastructure/config/env_config_provider.py`

### Behavior

- **Source**: `os.environ` entries that start with `<prefix>_` (default `APERILEX_`).
- **Key normalization**: Strips prefix, lowercases, and converts `__` to `.`.
  - Example: `APERILEX_DATABASE__POSTGRES__HOST` → `database.postgres.host`
- **Value parsing order**:
  1. `true`/`false` → `bool`
  2. integer → `int`
  3. float → `float`
  4. contains `,` → `list[str]`
  5. contains both `;` and `=` → `dict[str, str]` from `k=v;...`
  6. otherwise → `str`
- **Namespace view**: `get_namespace("database")` returns keys under `database.` with the prefix removed.
- **Writes**: `set("database.postgres.host", "x")` updates the cache and sets `APERILEX_DATABASE__POSTGRES__HOST` for child processes.
- **Export**: `export(include_sensitive=False)` masks sensitive keys by returning `"***MASKED***"`.

## DI wiring (runtime composition)

**Location**: `src/composition/provider_factory.py`

- Uses `EnvironmentConfigProvider(prefix="APERILEX")` as the only configuration source.

## Removed providers (redundant for Docker baseline)

- `JSONConfigProvider`: removed (unused; repo has no `config/` JSON runtime contract).
- `CompositeConfigProvider`: removed (no longer needed once config is env-only).
