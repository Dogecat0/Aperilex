# Aperilex - SEC Filing Analysis Engine

A modern, secure SEC filing analysis platform built with clean architecture principles. Aperilex leverages AI to provide intelligent analysis of SEC filings with a focus on security, scalability, and maintainability. (This is the rewrite version for the [SEC Filing Analysis Engine](https://github.com/Dogecat0/sec-filing-analysis).)

## Overview

Aperilex is designed to:
- Fetch and analyze SEC filings (10-K, 10-Q, 8-K) using the edgartools library
- Provide AI-powered insights and analysis through multiple LLM providers
- Offer a secure, scalable API for enterprise use
- Support background processing for large-scale analysis operations

## Architecture

The project follows Domain-Driven Design (DDD) and Clean Architecture principles:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                       │
│                    (FastAPI + Web Interface)                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                        Application Layer                        │
│                  (Use Cases / Command Handlers)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                         Domain Layer                            │
│              (Entities / Value Objects / Events)                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      Infrastructure Layer                       │
│        (Database / LLM Providers / External Services)           │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
aperilex/
├── src/
│   ├── domain/              # Business logic & entities
│   │   ├── entities/        # Analysis, Company, Filing
│   │   ├── value_objects/   # Money, ProcessingStatus, Ticker, FilingType
│   │   ├── events/
│   │   ├── exceptions/
│   │   └── services/        # Domain services
│   ├── application/         # Use cases & DTOs
│   │   ├── commands/        # AnalyzeFilingCommand
│   │   ├── queries/         # SearchFilingsQuery
│   │   └── handlers/
│   │   └── services/        # Application services
│   ├── infrastructure/      # External services
│   │   ├── database/
│   │   ├── llm/             # LLM provider abstractions
│   │   ├── sec_api/         # Direct edgartools integration
│   │   └── cache/
│   ├── presentation/        # REST API
│   │   └── api/
│   └── shared/              # Cross-cutting concerns
│       ├── config/
│       └── logging/
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   └── phases/              # Project phases documentation
└── CLAUDE.md                # AI assistant context
```

## Technology Stack

- **Language**: Python 3.12
- **Web Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **Cache**: Redis
- **Task Queue**: Celery
- **SEC Data**: edgartools (direct integration)
- **LLM Providers**: OpenAI, Anthropic (pluggable architecture)
- **Security**: JWT authentication, rate limiting, encryption

## Getting Started

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Poetry for dependency management

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/aperilex.git
cd aperilex
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start services:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
alembic upgrade head
```

### Development

Run all quality checks:
```bash
poetry run ruff check src/ && poetry run mypy src/ && poetry run black --check src/ && poetry run isort --check-only src/
```

Run tests:
```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific test file
pytest tests/unit/domain/
```

Format code:
```bash
poetry run black src/
poetry run isort src/
```

## API Usage

The API provides endpoints for:
- Filing analysis requests
- Analysis history retrieval
- Company information lookup
- Authentication and authorization

Example:
```bash
# Analyze a filing
POST /api/v1/analysis/filings/AAPL
{
  "filing_type": "10-K",
  "analysis_types": ["business", "risks", "financials"]
}
```

## Current Status

**Phase 2 Completed**: Core Domain Implementation
- ✅ Simplified domain layer focused on analysis
- ✅ Value objects with validation and type safety
- ✅ Comprehensive unit test coverage

**Next Phase**: Infrastructure Layer (Week 4)
- Direct edgartools integration
- LLM provider abstractions
- Repository implementations

See `docs/phases/` for detailed project timeline and completed phases.

## Security Features

- JWT-based authentication
- API key management with encryption
- Rate limiting per user/endpoint
- Input validation and sanitization
- SQL injection prevention via ORM
- Audit logging for compliance

## License

[License Type] - See LICENSE file for details