# Backend Testing Strategy and Notes

## Current Working Strategy (2025-09-30)

- Always run the full backend suite inside the compose image so secrets and DI wiring match runtime: `docker compose run --rm --no-deps app poetry run pytest`.
- Rebuild the app image (`docker compose build app`) after dependency or entrypoint changes so the container picks them up.
- `scripts/docker-entrypoint.sh` now exports `/app` onto `PYTHONPATH` and the base image ships with `pytest-asyncio`; no extra flags are required.
- Targeted runs follow the same pattern, e.g. `docker compose run --rm --no-deps app poetry run pytest tests/presentation/api/test_security.py -vv`.
- For quick unit-only feedback on the host, `PYTHONPATH=. poetry run pytest -m "unit"` still works because those suites avoid the DI bootstrap.
