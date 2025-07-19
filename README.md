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
│   │   ├── commands/        # Command handlers (ready for Phase 4)
│   │   ├── queries/         # Query handlers (ready for Phase 4)
│   │   └── handlers/
│   │   └── services/        # Application services
│   ├── infrastructure/      # External services (COMPLETED)
│   │   ├── database/        # SQLAlchemy models & migrations
│   │   ├── repositories/    # Repository pattern implementation
│   │   ├── llm/             # OpenAI provider with analysis schemas
│   │   ├── edgar/           # EdgarTools service integration
│   │   ├── cache/           # Redis caching layer
│   │   └── tasks/           # Celery background processing
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
- **Database**: PostgreSQL 16 with async SQLAlchemy 2.0+
- **Cache**: Redis 7 (multi-level caching with TTL strategies)
- **Task Queue**: Celery with Redis broker (background processing)
- **SEC Data**: edgartools library (Context7 Library ID: `/dgunning/edgartools`)
- **LLM Providers**: OpenAI (implemented), extensible for Anthropic, Gemini, Cohere
- **Infrastructure**: Docker & Docker Compose with production-ready services
- **Testing**: pytest with 242/242 tests passing (67.5% coverage)
- **Security**: Input validation, SQL injection prevention, container security

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

6. Validate installation (Phase 3):
```bash
python scripts/validate_phase3.py
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

## Infrastructure Features (Phase 3 Complete)

### SEC Filing Integration
- Direct access to SEC EDGAR database via edgartools
- Support for all filing types (10-K, 10-Q, 8-K, proxy statements)
- Financial statement parsing and XBRL data extraction
- Automatic rate limiting and SEC compliance

### AI-Powered Analysis
- OpenAI integration with structured output schemas
- Hierarchical analysis of filing sections:
  - Business overview and strategy analysis  
  - Risk factor assessment and categorization
  - Management Discussion & Analysis (MD&A) insights
  - Financial statement analysis and metrics
- Concurrent processing for large-scale operations

### Background Processing
- Celery task queue with Redis broker
- Dedicated queues for filing retrieval and analysis
- Async task monitoring and error handling
- Production task types: `fetch_company_filings`, `process_filing`, `analyze_filing`, `batch_analyze_filings`

### Caching & Performance
- Multi-level Redis caching with intelligent TTL strategies
- Company data: 24 hours
- Filing data: 12 hours  
- Analysis results: 6 hours
- Pattern-based cache invalidation for data consistency

## API Usage (Phase 4)

*The REST API endpoints will be implemented in Phase 4. Current infrastructure provides:*
- Repository pattern for data access
- Background task processing
- LLM analysis capabilities
- Complete database schema

Example planned endpoints:
```bash
# Analyze a filing (Phase 4)
POST /api/v1/analysis/filings/AAPL
{
  "filing_type": "10-K",
  "analysis_types": ["business", "risks", "financials"]
}
```

## Current Status

**Phase 3 Completed**: Infrastructure Layer Implementation
- ✅ Complete EdgarTools integration with SEC filing retrieval
- ✅ OpenAI LLM provider with structured analysis schemas
- ✅ Repository pattern with async SQLAlchemy 2.0+ support
- ✅ Celery background processing with Redis broker
- ✅ Multi-level caching layer with smart TTL strategies
- ✅ Production-ready Docker infrastructure
- ✅ **242/242 tests passing** with comprehensive coverage
- ✅ Database migrations and complete schema implementation

**Next Phase**: Application Services Layer (Phase 4)
- Use cases and command/query handlers
- REST API endpoint implementation
- Authentication and authorization
- Advanced analytics and reporting

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