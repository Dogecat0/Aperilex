# Backend coverage in docker

- Base image omits dev deps; pytest-cov not available by default. Network is restricted, so install transiently inside the app container when needed.
- One-shot coverage run (writes coverage file to `/tmp` to avoid permission errors):

```sh
docker compose run --rm --no-deps app sh -c 'pip install pytest-cov --target /tmp/.pip-deps && COVERAGE_FILE=/tmp/.coverage PYTHONPATH=/tmp/.pip-deps:$PYTHONPATH python -m pytest --cov=src --cov=tests --cov-report=term-missing'
```

- The pip install pulls pytest 9.x and will warn about pytest-asyncio pinning `<9`; current suites still pass, but rebuild the image with dev dependencies when network access is available to avoid drift.
- Containers are disposable; rerun the command after rebuilds or new shells because `/tmp/.pip-deps` is not persisted.***
