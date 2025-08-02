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
│   │   └── value_objects/   # Money, ProcessingStatus, Ticker, FilingType
│   ├── application/         # COMPLETED - Application Services Layer
│   │   ├── base/           # CQRS infrastructure (commands, queries, handlers)
│   │   ├── commands/       # Command handlers (filing analysis)
│   │   ├── queries/        # Query handlers (7 handlers implemented)
│   │   ├── schemas/        # Request/response DTOs and validation
│   │   ├── services/       # Application orchestrators and coordinators
│   │   ├── decorators/     # Caching and cross-cutting concerns
│   │   ├── patterns/       # Circuit breaker and resilience patterns
│   │   ├── factory.py      # Service factory
│   │   └── handlers_registry.py  # Handler registry
│   ├── infrastructure/      # External services (COMPLETED)
│   │   ├── database/        # SQLAlchemy models & migrations
│   │   ├── repositories/    # Repository pattern implementation
│   │   ├── llm/             # OpenAI provider with analysis schemas
│   │   ├── edgar/           # EdgarTools service integration
│   │   ├── cache/           # Redis caching layer
│   │   └── tasks/           # Celery background processing
│   ├── presentation/        # REST API (COMPLETED)
│   │   └── api/
│   │       └── routers/     # 8 API endpoints implemented
│   │           ├── analyses.py    # Analysis management endpoints
│   │           ├── companies.py   # Company research endpoints
│   │           ├── filings.py     # Filing analysis endpoints
│   │           ├── health.py      # System health endpoints
│   │           └── tasks.py       # Task tracking endpoints
│   └── shared/              # Cross-cutting concerns
│       ├── config/
│       └── logging/
├── tests/
│   ├── unit/                # Unit tests by layer
│   ├── integration/         # Integration tests (API, repositories)
│   ├── e2e/                 # End-to-end workflow tests
│   └── fixtures/            # Test data and fixtures
├── scripts/                 # Development and validation tools
│   ├── validate_phase3.py   # Infrastructure validation
│   ├── validate_api_integration.py  # API integration tests
│   └── generate_analysis_samples.py  # Sample data generation
├── docs/
│   ├── phases/              # Project phases documentation
│   ├── architecture/        # Architecture documentation
│   └── SETUP.md             # Setup instructions
├── mermaid/                 # Architecture diagrams
└── CLAUDE.md                # AI assistant context
```

## Technology Stack

### Core Technologies
- **Language**: Python 3.12 with strict type checking (MyPy)
- **Web Framework**: FastAPI with async/await support
- **Database**: PostgreSQL 16 with async SQLAlchemy 2.0+
- **Cache**: Redis 7 (multi-level caching with intelligent TTL strategies)
- **Task Queue**: Celery with Redis broker for background processing

### Architecture & Patterns
- **Clean Architecture**: Domain-driven design with clear layer separation
- **CQRS Pattern**: Command/query separation with dedicated handlers
- **Repository Pattern**: Async data access layer with comprehensive CRUD operations
- **Circuit Breaker**: Resilience patterns for external service integrations
- **Dependency Injection**: Service factory with constructor injection

### External Integrations
- **SEC Data**: edgartools library (Context7 Library ID: `/dgunning/edgartools`)
- **LLM Providers**: OpenAI (production), extensible for Anthropic, Gemini, Cohere
- **Background Processing**: Dedicated queues for filing retrieval and analysis

### Development & Quality
- **Testing**: pytest with 829/829 tests passing (79.63% coverage)
- **Type Safety**: Strict MyPy configuration with comprehensive type annotations
- **Code Quality**: Ruff linting, Black formatting, isort import sorting
- **Infrastructure**: Docker & Docker Compose with production-ready services
- **Security**: Input validation, SQL injection prevention, container security

### Production Features
- **38% Code Reduction**: Architectural optimization from 3,303 → 2,038 lines
- **Performance**: Async-first architecture with connection pooling
- **Monitoring**: Health endpoints and service status monitoring
- **Scalability**: Background task processing with queue management
- **Reliability**: Comprehensive error handling and circuit breaker patterns

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

6. Validate installation:
```bash
# Validate infrastructure (Phase 3)
python scripts/validate_phase3.py

# Validate API integration (Phase 4)
python scripts/validate_api_integration.py
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

## Development Scripts

### Validation & Testing
```bash
# Validate infrastructure layer (Phase 3)
python scripts/validate_phase3.py

# Validate API integration (Phase 4)
python scripts/validate_api_integration.py

# Generate sample analysis data for testing
python scripts/generate_analysis_samples.py
```

### Testing Structure
- **Unit Tests**: 242 tests covering all layers with domain logic focus
- **Integration Tests**: Repository, API, and service integration testing
- **End-to-End Tests**: Complete workflow validation from API to database
- **Test Coverage**: 67.5% with emphasis on critical business logic
- **Test Data**: Realistic fixtures and sample data for comprehensive testing

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

## API Endpoints (LIVE)

**Complete REST API implemented with 8 core endpoints:**

### Filing Analysis
```bash
# Trigger comprehensive filing analysis
POST /api/v1/filings/{accession}/analyze
{
  "analysis_template": "COMPREHENSIVE",
  "sections": ["business", "financials", "risks", "mda"]
}

# Get filing details and metadata
GET /api/v1/filings/{accession}

# Get analysis results for a filing
GET /api/v1/filings/{accession}/analysis
```

### Analysis Management
```bash
# List all analyses with pagination and filtering
GET /api/v1/analyses?page=1&limit=10&company_ticker=AAPL

# Get specific analysis by ID
GET /api/v1/analyses/{analysis_id}

# Get available analysis templates
GET /api/v1/analyses/templates
```

### Company Research
```bash
# Get company information by ticker
GET /api/v1/companies/{ticker}

# Get all analyses for a company
GET /api/v1/companies/{ticker}/analyses
```

### System Health
```bash
# System status and service health monitoring
GET /api/v1/health
```

## Current Status

**Phase 4 COMPLETED**: Application Services & API Implementation
- ✅ **Complete CQRS architecture** with 8 command/query handlers implemented
- ✅ **Full REST API** with 8 core endpoints operational (filing, analysis, company, health)
- ✅ **Application services layer** with orchestrators and coordinators
- ✅ **Advanced patterns** (circuit breaker, caching decorators, resilience patterns)
- ✅ **38% code reduction** (3,303 → 2,038 lines) through architectural optimization
- ✅ **242/242 tests passing** with comprehensive coverage across all layers
- ✅ **Production-ready API** with background task integration and error handling
- ✅ **Enhanced type safety** with CIK/Ticker type wrappers and schema standardization

**Infrastructure Foundation (Phases 1-3)**:
- ✅ Complete EdgarTools integration with SEC compliance
- ✅ OpenAI LLM provider with structured analysis schemas
- ✅ Repository pattern with async SQLAlchemy 2.0+ support
- ✅ Celery background processing with Redis broker
- ✅ Multi-level caching layer with smart TTL strategies
- ✅ Production-ready Docker infrastructure

**Next Phase**: Presentation Layer (Phase 5)
- Web-based user interface built on the REST API
- Interactive dashboards for financial analysis
- User-friendly forms for filing analysis requests
- Data visualization and charting components
- Responsive design for desktop and mobile

**Future Phase**: Enhanced Features (Phase 6)
- Authentication and authorization system
- Advanced analytics and monitoring
- Performance optimizations and scaling

**Project Status**: Production-ready financial analysis platform with complete backend infrastructure, operational API endpoints, and comprehensive testing.

See `docs/phases/` for detailed project timeline and completed phases.

## Security Features

- JWT-based authentication
- API key management with encryption
- Rate limiting per user/endpoint
- Input validation and sanitization
- SQL injection prevention via ORM
- Audit logging for compliance

## License

[License Type] - See LICENSE file for details# test
