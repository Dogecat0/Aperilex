# Vulture Dead Code Detection

Vulture is a static analysis tool that scans Python projects for unused code. This guide covers the core usage we recommend for the Aperilex backend.

## Installation

Vulture is already listed under Poetry's development dependencies. Run `poetry install` to ensure the tool is available:

```bash
poetry install
```

## Core Usage

Run Vulture against the application and test sources to identify potentially dead code:

```bash
poetry run vulture src tests --min-confidence 80
```

- `src` and `tests` target runtime and supporting code.
- `--min-confidence 80` filters out lower-confidence findings that are more likely to be false positives. Increase the threshold (e.g., 90) when you want to focus on the most suspicious results.

There is also a Makefile helper that wraps the same command:

```bash
make deadcode
```

## Handling False Positives

Dynamic attribute access, type-check-only imports, or framework callbacks sometimes appear unused. When a finding is intentional:

1. Try to make the usage explicit (e.g., by importing or referencing the symbol directly).
2. If that is not possible, whitelist it in a `vulture_whitelist.py` file or via the command line.

### Whitelist File

Create a `vulture_whitelist.py` next to the module that triggers a false positive (or in the project root) with assignments for each intentional symbol:

```python
# vulture_whitelist.py
from src.shared.config import settings

settings  #: used via dynamic attribute access
```

Then include the whitelist when running Vulture:

```bash
poetry run vulture src tests vulture_whitelist.py --min-confidence 80
```

### Ignore Patterns

Use `--exclude` for paths and `--ignore-names` for functions or variables that follow a specific naming pattern:

```bash
poetry run vulture src tests --min-confidence 80 --exclude "src/presentation/api/routers/__init__.py" --ignore-names "*_schema"
```

Keep ignore rules minimal and justify additions in pull requests.

## Workflow Recommendation

1. Run `make deadcode` locally before refactors that touch large areas of the codebase.
2. Review high-confidence reports first; remove dead code where feasible.
3. Add whitelists only when the code is truly exercised indirectly (framework callbacks, reflection, dynamic imports).
4. Capture any permanent whitelist entries in code review notes so the team knows why they exist.

## Next Steps

- Decide whether to add Vulture to CI once the baseline is clean.
- Consider storing a shared whitelist (e.g., `tools/vulture_whitelist.py`) if multiple modules require exemptions.
- Periodically run Vulture on feature branches to prevent dead code from accruing over time.
