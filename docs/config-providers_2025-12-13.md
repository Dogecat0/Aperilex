# Config Providers (2025-12-13)

## Summary

- `EnvironmentConfigProvider`: Reads `APERILEX_*` environment variables into an in-memory cache, performs lightweight type coercion, and masks sensitive keys on export.
- `JSONConfigProvider`: Reads a JSON file, flattens nested objects into dot-delimited keys, persists on every `set()`/`delete()`, and masks sensitive keys on export.
- `CompositeConfigProvider`: Wraps multiple providers with ordered precedence; reads return the first hit, writes go to the highest-precedence provider, and merged views are built lower → higher precedence.

## EnvironmentConfigProvider

**Location**: `src/infrastructure/config/env_config_provider.py`

### Behavior

- **Source**: `os.environ` entries that start with `<prefix>_` (default `APERILEX_`).
- **Key normalization**: Strips prefix, lowercases, and stores:
  - the raw normalized key (e.g., `AUTHENTICATION__JWT_ISSUER` → `authentication__jwt_issuer`)
  - a dotted variant where `__` becomes `.` (e.g., `authentication.jwt_issuer`)
- **Value parsing order**:
  1. `true`/`false` → `bool`
  2. integer → `int`
  3. float → `float`
  4. contains `,` → `list[str]`
  5. contains both `;` and `=` → `dict[str, str]` from `k=v;...`
  6. otherwise → `str`
- **Writes**: `set()` updates the in-memory cache and also sets the corresponding `APERILEX_<KEY>` environment variable for child processes.
- **Namespace view**: `get_namespace(namespace)` selects cached keys with an underscore prefix match (`f"{namespace.lower()}_"`) and returns entries with that prefix removed.
- **Export**: `export(include_sensitive=False)` masks sensitive keys by returning `"***MASKED***"` for values.

### Observed mismatches

- The provider supports hierarchical lookups via dotted keys, but `get_namespace()` uses underscore prefix matching, so namespace introspection does not align with the dotted key convention.
- For env vars using `__` nesting (e.g., `APERILEX_AUTHENTICATION__JWT_ISSUER`), `get_namespace("authentication")` matches `authentication__...` and produces a leading-underscore key segment after slicing (e.g., `_jwt_issuer`), which is not a stable/clean namespace contract.

## JSONConfigProvider

**Location**: `src/infrastructure/config/json_config_provider.py`

### Behavior

- **Source**: A JSON file at `file_path`.
- **Flattening model**: Nested objects are flattened into dot-delimited, lowercase lookup keys (e.g., `{"authentication": {"jwt_issuer": "x"}}` → `authentication.jwt_issuer`).
- **Display keys**: Maintains an internal `_key_index` so `list_keys()`/`export()` can use original segment casing from the file (while lookups remain case-insensitive).
- **Persistence**: `set()` and `delete()` rewrite the JSON file by rebuilding a nested structure from the flattened cache.
- **Value coercion**: Primitives are preserved; JSON arrays become `list[str]`. Sensitive keys are masked on `export()` unless `include_sensitive=True`.
- **Namespace view**: `get_namespace("authentication")` returns keys under `authentication.` with the prefix removed.

### Observed mismatches

- Leaf JSON objects are always treated as nested namespaces during load (recursive flattening). This prevents `dict[str, str]` values from round-tripping through disk:
  - `set("x", {"a": "b"})` writes a JSON object
  - a subsequent reload flattens it into `x.a="b"` instead of preserving `x` as a `dict`
  - `get_dict("x")` therefore cannot reliably work after reload

## CompositeConfigProvider

**Location**: `src/infrastructure/config/composite_config_provider.py`

### Behavior

- **Precedence**: Provider list order defines priority.
  - `get()` returns the first provider where `exists()` is true.
  - `get_namespace()` and `export()` merge providers by iterating in reverse and `update()`-ing so higher-precedence values overwrite lower-precedence values.
- **Writes**:
  - `set()` writes only to the first provider (highest precedence).
  - `delete()` attempts deletion across all providers.
- **Reload**: Calls `reload()` on all providers.

### Redundant logic with current providers

- `get()` includes an extra lookup path that retries with the original key casing. Current providers are already case-insensitive and normalize keys internally, so this path adds complexity without changing behavior unless a future provider is case-sensitive.

## DI wiring (runtime composition)

**Location**: `src/composition/provider_factory.py`

- Always registers `EnvironmentConfigProvider(prefix="APERILEX")` as the highest-precedence source.
- Optionally adds JSON config sources if `config/` exists:
  - `config/<environment>.json`
  - `config/default.json`
- If more than one source exists, wraps them in `CompositeConfigProvider` so environment values override JSON.

## Cleanup candidates (redundant or unused behavior)

- `JSONConfigProvider._require_exists()` exists but is unused.
- `ConfigValidationRule.regex_pattern` exists in the interface but is ignored by both providers; `validate()` uses substring matching only.
- `EnvironmentConfigProvider` caches both underscore and dotted key variants for the same env var; `list_keys()`/`export()` expose both variants, which can duplicate semantically identical settings.

