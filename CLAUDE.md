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

3. **Financial Analysis Tools**:
   - **Important Note**: Aperilex does NOT use XBRL for financial data extraction at this stage
   - Financial statements are accessed as text through filing objects
   - The system relies on LLM analysis to interpret financial data rather than structured parsing

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
   # Aperilex Implementation Pattern (NOT using XBRL)
   # Financial data is extracted as text from filing objects
   filing_obj = filing.obj()

   # Check for financial statement attributes
   if hasattr(filing_obj, "balance_sheet"):
       balance_sheet_text = str(filing_obj.balance_sheet)
   if hasattr(filing_obj, "income_statement"):
       income_statement_text = str(filing_obj.income_statement)
   if hasattr(filing_obj, "cash_flow_statement"):
       cash_flow_text = str(filing_obj.cash_flow_statement)

   # Financial data is then analyzed by LLM for insights
   # NOT parsed into structured numeric values
   ```

## Development Workflow

**IMPORTANT**: Please work through the tasks in docs/tasks/tasks.md one at a time and mark each finished task with X.

For complex development tasks, you must try to use specialized sub-agents that understand Aperilex's architecture and requirements, and each sub-agent has a specific focus area and each sub-agent should use `explore-review-code-test.md` working pattern. Also use `Context7` accordingly based on tech stack to search for latest doc if you have any questions or encountering any issues you are not sure about, not other ways like direct url/web search.

### Quick Command Reference
```bash
# Environment setup
poetry install && docker-compose up -d && alembic upgrade head

# Fast quality check
poetry run mypy src/ && poetry run ruff check src/

# Development test cycle
pytest tests/unit/ -m "not external_api" --cov=src

# Full quality suite (use code-quality agent for detailed analysis)
poetry run ruff check src/ && poetry run mypy src/ && poetry run black --check src/ && poetry run isort --check-only src/
```

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

### Code quality check Workflow
**IMPORTANT**: For quick checks:
```bash
# Before starting development (or use aperilex-code-quality agent)
poetry run mypy src/ && poetry run ruff check src/

# After making changes (or use aperilex-code-quality agent for comprehensive analysis)
poetry run black src/ && poetry run isort src/ && poetry run mypy src/

# Use aperilex-test-strategy agent for intelligent test execution
poetry run pytest
```

## LLM Integration

**CRITICAL REQUIREMENT**: ALL insights, analysis, summaries, and interpretations of SEC filings MUST be LLM-powered. Never implement hardcoded logic or fake analysis functions.

### Current LLM Implementation

Aperilex currently uses OpenAI as the sole LLM provider (`infrastructure.llm.openai_provider.OpenAIProvider`) with comprehensive filing analysis capabilities:

**Core Analysis Features**:
- **Filing-Level Analysis**: Complete SEC filing analysis with executive summary, key insights, financial highlights, risk factors, and growth opportunities
- **Section-Level Analysis**: Detailed breakdown of specific filing sections with consolidated insights and sentiment scoring
- **Sub-Section Analysis**: Granular analysis using specialized schemas for business operations, financials, risks, and management discussions

**Supported Analysis Schemas**:
- Business Analysis (operations, products, competitive advantages, strategy)
- Financial Statement Analysis (balance sheet, income statement, cash flow)
- Risk Factors Analysis
- Management Discussion & Analysis (MD&A)

### LLM powered analysis implementation Requirements

**IMPORTANT**: When implementing ANY feature that involves understanding, summarizing, or extracting insights from filings:
1. **Always Use LLM for Insights**: Never implement hardcoded analysis logic
2. **Follow Existing Patterns**: Check `infrastructure/llm/` for current capabilities
3. **Extend Properly**: Add new analysis methods and Pydantic schemas when needed

**Architecture Pattern**:
```python
# CORRECT: Using LLM for insights
llm_provider = get_llm_provider()
analysis = llm_provider.analyze_filing(filing_data, template="FINANCIAL_FOCUSED")

# INCORRECT: Hardcoded analysis
def extract_revenue_growth(filing_text):
    # Never do this - use LLM instead
    return "Revenue grew 10%"  # ❌ WRONG
```

### Future LLM Enhancements

The system is designed for multi-provider support. Future providers should implement the `BaseLLMProvider` interface and maintain the same analysis capabilities.

## Phase Reference

**General Phase Information**: See `docs/phases/PHASES.md` for completed phases and detailed project info.

**Detailed Plan**: See `docs/phases/PHASE_*_DETAILED_PLAN.md`.

**Phase Notes**: When creating new phase plans, no need to add timeline information, no need to provide example code.

**Current Tasks**: See `docs/tasks/tasks.md`.
