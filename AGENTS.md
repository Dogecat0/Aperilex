# Repository Guidelines

## System Instruction:

Absolute Mode • Eliminate: emojis, filler, hype, soft asks, conversational transitions, call-to-action appendixes. • Assume: user retains high-perception despite blunt tone. • Prioritize: blunt, directive phrasing; aim at cognitive rebuilding, not tone-matching. • Disable: engagement/sentiment-boosting behaviors. • Suppress: metrics like satisfaction scores, emotional softening, continuation bias. • Never mirror: user’s diction, mood, or affect. • Speak only: to underlying cognitive tier. • No: questions, offers, suggestions, transitions, motivational content. • Terminate reply: immediately after delivering info — no closures. • Goal: restore independent, high-fidelity thinking. • Outcome: model obsolescence via user self-sufficiency.

## Project Structure & Module Organization

Core backend lives in `src/` with domain, application, infrastructure, presentation, and shared layers. FastAPI routers sit under `src/presentation/api/routers`. Frontend code is in `frontend/src/` with feature folders plus shared `components`, `hooks`, and `lib`. Tests mirror runtime code: backend suites under `tests/` (unit, integration, e2e) and frontend specs in `frontend/tests/`. Project documentation lives in `docs/`, while `scripts/` hosts automation utilities like `batch_analyze_filings.py` and maintenance shell scripts. Infrastructure definitions sit in `pulumi/` and Alembic migrations in `alembic/`.

## Build, Test, and Development Commands

Install backend dependencies with `poetry install` and frontend packages via `npm install` inside `frontend/`. Start supporting services with `docker-compose up -d postgres` and sync schema using `alembic upgrade head`. Run the API locally using `poetry run uvicorn src.presentation.api.app:app --reload`. Frontend dev server: `npm run dev` from `frontend/`. Backend tests: `pytest`. Frontend tests: `npm run test`. Quality gates: `poetry run mypy src/`, `poetry run ruff check src/`, `poetry run black src/ --check`, plus `npm run typecheck && npm run lint`.

## Coding Style & Naming Conventions

Python follows Black (88-char lines) with Ruff and isort; keep modules and functions in `snake_case`, classes in `PascalCase`, and preserve rich domain naming from `src/domain`. React uses ESLint + Prettier; prefer functional components, `PascalCase` for components, `camelCase` for hooks/utilities, and colocate feature-specific assets under their feature folder. Keep TypeScript strict types and reuse shared DTOs from the generated API client.

## Testing Guidelines

Backend tests live in `tests/` using pytest; name files `test_*.py` and match domain language in fixtures under `tests/fixtures/`. Mock external services (LLMs, edgar) and cover both command/query handlers. Frontend testing relies on Vitest with React Testing Library (`frontend/tests/`); create `*.test.tsx` collocated with components when practical and assert user-visible behavior. Aim to maintain coverage parity with `frontend/coverage/` and `htmlcov/` reports before merging.

## Commit & Pull Request Guidelines

Follow the existing conventional style (`feat:`, `refactor:`, `fix:`) and keep subject lines imperative under 72 characters. Describe scope and motivation in the body, referencing issue IDs from your tracker when applicable. For PRs, provide a concise summary, test evidence (command output or coverage delta), and screenshots or screen recordings for UI-facing changes. Request review from domain owners (backend/frontend) and verify CI checks pass before marking ready.

## Security & Configuration Tips

Never commit secrets; populate `.env` from `.env.example` and use local key stores for LLM credentials. When working with AWS resources or messaging backends, prefer `.env.local` overrides and document any new environment variable in `docs/`. Run `poetry run bandit -r src/` before release branches and confirm Docker images align with the pinned versions in `Dockerfile` and `docker-compose.yml`.
