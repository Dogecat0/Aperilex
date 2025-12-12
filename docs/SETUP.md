# Development Setup Guide

This guide will help you set up the Aperilex development environment.

## Prerequisites

### Required Software

- **Python 3.12+**: Download from [python.org](https://www.python.org/downloads/)
- **Poetry**: Python dependency management
- **Docker & Docker Compose**: For local services
- **Git**: Version control

### Installation Commands

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Verify installations
python --version    # Should be 3.12+
poetry --version   # Should be 1.0+
docker --version   # Should be 20.0+
git --version      # Any recent version
```

## Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/aperilex.git
cd aperilex
```

### 2. Install Dependencies

```bash
# Install all dependencies and pre-commit hooks
make install

# Or manually:
poetry install
poetry run pre-commit install
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Stage 5 routes all credentials through Docker secrets. After copying the
templates, bootstrap the secrets volume:

```bash
mkdir -p .secrets

# Base Postgres secret used by docker-entrypoint
echo "dev_password" > .secrets/postgres_password
chmod 600 .secrets/postgres_password

# Generate JWT signing keys (writes JWT_PRIVATE_KEY/JWT_PUBLIC_KEY)
docker compose run --rm app python scripts/generate_jwt_keys.py

# Add Google OAuth credentials (values provided by platform team)
echo "your-google-client-id" > .secrets/GOOGLE_CLIENT_ID
echo "your-google-client-secret" > .secrets/GOOGLE_CLIENT_SECRET
chmod 600 .secrets/GOOGLE_CLIENT_*

# Add LLM and Google API keys (optional for local analysis/testing)
echo "your-openai-api-key" > .secrets/openai_api_key
echo "your-google-api-key" > .secrets/google_api_key
chmod 600 .secrets/openai_api_key .secrets/google_api_key
```

Edit `.env` to adjust non-secret settings (feature flags, logging levels, etc.)
as needed. Database passwords and OAuth keys should remain exclusively in the
`.secrets/` files configured above.

Edit `frontend/.env` for the Vite dev server:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

The production build pulls values from `frontend/.env.production`, which points the UI to the public API (`https://www.aperilexlabs.com`).

### 4. Start Development Services

```bash
# Start PostgreSQL and RabbitMQ
make docker-up

# Or manually:
docker-compose up -d
```

### 5. Database Setup

```bash
# Run migrations (when implemented)
make migrate

# Or manually:
poetry run alembic upgrade head
```

## Development Workflow

### Starting Development

```bash
# Start all services
make dev

# Or start API only (requires running docker services)
poetry run uvicorn src.presentation.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (in debug mode)
- **Database**: localhost:5432
- **RabbitMQ**: localhost:5672 (management UI at http://localhost:15672)

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
poetry run pytest tests/unit/test_example.py -v

# Run tests with specific marker
poetry run pytest -m "unit" -v
```

### Code Quality Checks

```bash
# Run all quality checks
make pre-commit

# Individual checks
make lint          # Linting
make format        # Code formatting
make type-check    # Type checking
make security      # Security scanning
```

### Regenerating API contract artifacts

Whenever you update the analysis DTOs or FastAPI routes, regenerate the stored
OpenAPI schema and the TypeScript client types so the frontend stays in sync:

```bash
# From the repository root
poetry run poe generate_openapi

# Rebuild the TypeScript types (produces frontend/src/lib/types/generated.ts)
poetry run poe generate_client
```

Both commands run locally against the codebase; no docker containers or running
API server are required.

### Making Changes

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes and test**
   ```bash
   # Make your changes
   make test
   make pre-commit
   ```

3. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature
   ```

## IDE Configuration

### VS Code

Install recommended extensions:
- Python
- Pylance
- Python Docstring Generator
- GitLens
- Docker

Configuration in `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### PyCharm

1. Open project in PyCharm
2. Set interpreter to Poetry environment
3. Enable code style settings:
   - Black for formatting
   - isort for imports
   - Enable type checking

## Troubleshooting

### Common Issues

**Poetry installation fails**
```bash
# Try alternative installation
pip install poetry
```

**Docker permission denied**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Logout and login again
```

**Port already in use**
```bash
# Check what's using the port
lsof -i :8000
# Kill the process or change port in docker-compose.yml
```

**Database connection fails**
```bash
# Check if PostgreSQL is running
docker-compose ps
# Check logs
docker-compose logs postgres
```

**Pre-commit hooks fail**
```bash
# Update hooks
poetry run pre-commit autoupdate
# Run manually
poetry run pre-commit run --all-files
```

### Performance Tips

- Use `make dev` for fastest startup
- Run only necessary services during development
- Use pytest markers to run specific test groups
- Enable Docker BuildKit for faster builds

### Environment Variables

For security, never commit real secrets. Use:
- `.env` for local development
- `.env.example` as template
- Environment-specific files: `.env.dev`, `.env.test`, `.env.prod`

## Next Steps

Once setup is complete:

1. Explore the codebase structure
2. Run the test suite
3. Read the architecture documentation

Happy coding! 🚀
