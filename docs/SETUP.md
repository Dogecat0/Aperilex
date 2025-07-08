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
```

Edit `.env` file with your configuration:

```env
# Database
DATABASE_URL=postgresql+asyncpg://aperilex:dev_password@localhost:5432/aperilex

# Redis
REDIS_URL=redis://localhost:6379

# Security (generate secure keys for production)
SECRET_KEY=your-super-secret-jwt-key-at-least-32-characters-long
ENCRYPTION_KEY=your-encryption-key-for-sensitive-data-32-chars

# LLM Providers (optional for initial setup)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# SEC API
SEC_USER_AGENT=your-email@example.com
```

### 4. Start Development Services

```bash
# Start PostgreSQL and Redis
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
- **Redis**: localhost:6379

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