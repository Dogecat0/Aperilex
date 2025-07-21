# Aperilex Development Context

## Project Overview
Aperilex is an open-source financial analysis platform that makes SEC filings accessible and understandable for everyone. Whether you're an investor, analyst, student, or simply curious about public companies, Aperilex transforms complex financial documents into clear, actionable insights.

**Mission**: Democratize financial analysis by making SEC filings as easy to understand as reading a news article.

Aperilex provides:
- **User-Friendly Interface**: Web-based dashboard that anyone can use, no financial expertise required
- **AI-Powered Insights**: Automatic extraction of key risks, opportunities, and financial trends from filings
- **Visual Financial Analysis**: Charts, graphs, and comparisons that make complex data understandable
- **Smart Summaries**: Plain-English explanations of what filings mean for investors
- **Company Research Tools**: Compare companies, track changes over time, and identify trends
- **Developer API**: Powerful REST API for building financial applications and integrations
- **Advanced Technical Architecture**: Robust backend using edgartools library with multiple LLM providers

## EdgarTools Reference

**EdgarTools Integration Note**: All implementations should reference Context7 Library ID `/dgunning/edgartools` for examples and patterns. We should always use this as edgartool reference, not other ways like direct url/web search.

The previous version used edgartools (Context7 Library ID: `/dgunning/edgartools`), a Python library for accessing SEC EDGAR filings. Based on the Context7 documentation, here's what we need to know:

### Core EdgarTools Features
- **Simple API**: Access any SEC filing with just a few lines of code
- **Smart Parsing**: Automatically converts raw filings (HTML, XML, XBRL) to structured Python objects
- **Comprehensive Coverage**: Supports all filing types (10-K, 10-Q, 8-K, 13F, Forms 3/4/5, etc.)
- **XBRL Support**: Extract structured financial data with advanced querying capabilities
- **No API Keys**: Uses SEC's free public APIs with built-in rate limiting

### Key Classes and Components

1. **Company**: Main entry point for company data
   - Initialized by ticker or CIK: `Company("AAPL")` or `Company(320193)`
   - Methods: `get_filings()`, `get_financials()`, `get_facts_for_namespace()`, `get_insider_transactions()`
   - Access financial statements directly: `company.financials.balance_sheet()`

2. **Filing**: Represents individual SEC filings
   - Methods: `.obj()`, `.html()`, `.text()`, `.markdown()`, `.xml()`, `.attachments`
   - Converts to form-specific data objects automatically
   - Text extraction for LLM processing: `.chunk_text(chunk_size=4000)`

3. **XBRL and Financial Statements**:
   - `XBRL.from_filing(filing)`: Parse XBRL data from filings
   - `XBRLS.from_filings(filings)`: Stitch multiple periods together
   - Access statements: `xbrl.statements.balance_sheet()`, `.income_statement()`, `.cashflow_statement()`
   - Convert to DataFrames: `.to_dataframe()`, `.to_markdown()`

4. **Financial Analysis Tools**:
   - `FinancialRatios(xbrl)`: Calculate liquidity, profitability, leverage ratios
   - Time series analysis: `facts.time_series('Revenue')`
   - Custom metric extraction: `financials.get_fact_for_metric("CustomXBRLConcept")`

5. **Specialized Features**:
   - **Investment Funds**: `Fund`, `FundClass`, portfolio holdings analysis
   - **Insider Trading**: Parse Forms 3/4/5, aggregate transactions
   - **Ownership Documents**: `Ownership.from_xml(xml)` for detailed transaction data

### Important Implementation Considerations

1. **SEC Identity Requirement**: Must set user identity for compliance
   ```python
   from edgar import *
   set_identity("your.name@company.com")  # Required by SEC
   ```

2. **Rate Limiting**: Automatic handling with three modes
   - Built-in retry logic and connection management
   - Respects SEC rate limits automatically

3. **Data Access Patterns**:
   ```python
   # Company → Filings → Filing → Data Object → Specific Data
   company = Company("MSFT")
   filings = company.get_filings(form="10-K")
   latest_10k = filings.latest()
   tenk = latest_10k.obj()  # Structured Form10K object
   balance_sheet = tenk.financials.balance_sheet
   ```

4. **Advanced XBRL Capabilities**:
   - Query by statement type, value thresholds, periods
   - Multi-period stitching for trend analysis
   - Financial fact extraction with time series support

### Example Implementation Patterns

```python
# Quick example of core edgartools usage
from edgar import *
set_identity("aperilex@company.com")

# Get company and financials
company = Company("AAPL")
financials = company.get_financials()
balance_sheet = financials.balance_sheet()

# Multi-period analysis
filings = company.get_filings(form="10-K").head(3)
xbrls = XBRLS.from_filings(filings)
income_trend = xbrls.statements.income_statement()

# Financial ratios
from edgar.xbrl.analysis.ratios import FinancialRatios
ratios = FinancialRatios(xbrl)
liquidity = ratios.calculate_liquidity_ratios()
```

### Aperilex Enhancement Opportunities

#### User-Focused Features
1. **Interactive Visualizations**: Charts and graphs for financial trends, ratios, and comparisons
2. **Smart Alerts**: Notify users of significant changes in filings or financial metrics
3. **Company Comparison Tools**: Side-by-side analysis of multiple companies
4. **Portfolio Tracking**: Monitor holdings and get insights on owned companies
5. **Educational Content**: Explanations and tutorials for financial concepts
6. **Export & Sharing**: Generate reports, PDFs, and shareable insights
7. **Mobile Experience**: Responsive design for mobile financial research

#### Technical Infrastructure
1. **Caching Layer**: Redis caching for frequently accessed filings and parsed XBRL data
2. **Advanced LLM Integration**: Multi-provider AI for intelligent filing analysis and summarization
3. **Real-time Processing**: WebSocket updates for live analysis and notifications
4. **Data Pipeline**: ETL pipeline for continuous filing updates and analysis
5. **Advanced Analytics**: Peer comparison, trend detection, and anomaly detection algorithms
6. **Performance Monitoring**: Metrics for API usage, edgartools performance, and user experience
7. **Background Processing**: Celery for large-scale XBRL parsing and analysis operations

## Development Commands

### Setup
```bash
# Install dependencies
poetry install

# Start services
docker-compose up -d

# Run migrations
alembic upgrade head
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/unit/test_domain_models.py
```

### Code Quality
```bash
# Type checking
poetry run mypy src/

# Linting
poetry run ruff check src/

# Format code
poetry run black src/
poetry run isort src/

# Run all quality checks
poetry run ruff check src/ && poetry run mypy src/ && poetry run black --check src/ && poetry run isort --check-only src/
```

### Security
```bash
# Security scan
bandit -r src/

# Dependency vulnerabilities
safety check
```

## Architecture Notes

Aperilex uses clean architecture principles to enable both powerful user features and robust technical capabilities:

- **Domain Layer**: Core business entities and logic (Filing, Company, Analysis) that represent real-world financial concepts
- **Application Layer**: Use cases and commands (AnalyzeFilingCommand, SearchFilingsQuery) that orchestrate user workflows
- **Infrastructure Layer**: External integrations (SEC API, LLM providers, Database) that power data access and AI insights
- **Presentation Layer**: Both REST API endpoints for developers AND web UI for end users

## Git Integration
Before any code changes or implementation, ensure we are in the correct Git branch that follows the best git practice and the development plan in `docs/phases/PHASE_*_DETAILED_PLAN.md`:

```bash
# Check current branch
git branch

# Switch to or create the appropriate feature branch
git checkout -b feature/your-feature-name

# Or switch to existing feature branch
git checkout feature/existing-feature
```

## Code Quality Standards

### Engineering Practices
- **SOLID Principles**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **Clean Code**: Meaningful names, small functions (<20 lines), single responsibility per function
- **Domain-Driven Design**: Clear separation of entities, value objects, and aggregates that model real financial concepts
- **Immutability**: Value objects should be immutable, use dataclasses with `frozen=True`
- **Dependency Injection**: Use constructor injection, depend on abstractions not concretions
- **Error Handling**: Use custom exceptions for domain errors, fail fast with clear error messages
- **Testing**: Unit tests for domain logic, integration tests for external dependencies
- **User-Centric Design**: Every technical decision should ultimately serve end-user value

### Type Checking
- **MyPy**: Strict type checking enabled with targeted overrides in `pyproject.toml`
- **Return Types**: All functions must have explicit return type annotations
- **Pydantic v2**: Use `validation_alias` instead of deprecated `env` parameter
- **SQLAlchemy**: Use `async_sessionmaker` for async database sessions

### Development Workflow
**IMPORTANT**: Always run type checking and linting before implementing features:
```bash
# Before starting development
poetry run mypy src/ && poetry run ruff check src/

# After making changes
poetry run black src/ && poetry run isort src/ && poetry run mypy src/

# Use poetry to run any tests when needed
poetry run pytest
```

### MyPy Configuration
The following overrides are configured in `pyproject.toml`:
- `src.shared.config.settings`: Disabled `call-arg` errors for Settings instantiation
- `src.infrastructure.database.base`: Disabled `misc` errors for DeclarativeBase overrides

## Phase Reference

**General Phase Information**: See `docs/phases/PHASES.md` for completed phases and detailed project info.

**Detailed Plan**: See `docs/phases/PHASE_*_DETAILED_PLAN.md`.

**Phase Notes**: When creating new phase plans, no need to add timeline information, no need to provide example code.