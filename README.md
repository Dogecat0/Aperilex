# Aperilex - AI-Powered Financial Analysis Platform

**Democratize financial analysis by making SEC filings as easy to understand as reading a news article.**

Aperilex is an open-source financial analysis platform that transforms complex SEC filings into clear, actionable insights. Whether you're an investor, analyst, student, or simply curious about public companies, Aperilex provides AI-powered analysis through an intuitive web interface and powerful developer API.

## 🚀 What Aperilex Does

**For Everyone:**
- **🔍 Smart Company Research**: Search any public company and get instant insights
- **📊 AI-Powered Analysis**: Automatic extraction of key risks, opportunities, and financial trends
- **📈 Interactive Dashboards**: Comprehensive analysis tracking with visual progress indicators
- **💾 Export & Sharing**: Generate PDF reports and JSON file of analysis results
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices

**For Developers:**
- **🔌 REST API**: Complete API with 13+ endpoints for financial data integration
- **⚡ Background Processing**: Scalable async analysis with progress tracking
- **📚 TypeScript Support**: Full type definitions for seamless integration

**Key Features:**
- Complete web application with React 19 interface
- AI-powered SEC filing analysis (10-K, 10-Q)
- Plain-English summaries of complex financial documents
- Risk factor analysis and business opportunity identification
- Financial metrics visualization with interactive charts
- Company comparison and trend analysis tools

## 🏗️ Architecture

Aperilex is a **complete full-stack application** built with clean architecture principles:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│              React 19 + TypeScript + Tailwind CSS              │
│          (47+ Components, Dashboards, Visualizations)          │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API + TypeScript Client
┌───────────────────────────────▼─────────────────────────────────┐
│                      Presentation Layer                         │
│          FastAPI REST API (13+ Endpoints + OpenAPI)            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      Application Layer                          │
│                (CQRS Commands/Queries + Handlers)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                        Domain Layer                             │
│           (Rich Entities + Value Objects + Business Rules)      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    Infrastructure Layer                         │
│       (PostgreSQL + Redis + EdgarTools + OpenAI + Celery)      │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

**Full-Stack Application Structure:**

```
aperilex/
├── frontend/                # 🎨 REACT WEB APPLICATION (COMPLETED)
│   ├── src/
│   │   ├── components/      # 47+ React components
│   │   │   ├── analysis/    # Analysis results & visualizations
│   │   │   ├── charts/      # Financial data charts (Recharts)
│   │   │   ├── layout/      # App shell, header, navigation
│   │   │   └── ui/          # Design system components
│   │   ├── features/        # Feature-based modules
│   │   │   ├── analyses/    # Analysis management
│   │   │   ├── companies/   # Company research
│   │   │   ├── dashboard/   # Interactive dashboard
│   │   │   └── filings/     # SEC filing exploration
│   │   ├── api/            # TypeScript API client
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # React Query, Zustand config
│   │   └── utils/          # Helper functions
│   ├── coverage/           # Test coverage reports
│   └── tests/              # 1,444+ frontend tests
├── src/                    # 🔧 BACKEND API (COMPLETED)
│   ├── domain/             # Business logic & entities
│   │   ├── entities/       # Analysis, Company, Filing
│   │   └── value_objects/  # Money, ProcessingStatus, Ticker
│   ├── application/        # CQRS application services
│   │   ├── commands/       # Command handlers (analysis orchestration)
│   │   ├── queries/        # Query handlers (8 implemented)
│   │   ├── schemas/        # Pydantic DTOs & validation
│   │   ├── services/       # Application orchestrators
│   │   └── patterns/       # Circuit breaker, resilience
│   ├── infrastructure/     # External integrations
│   │   ├── database/       # PostgreSQL with SQLAlchemy
│   │   ├── repositories/   # Async repository pattern
│   │   ├── llm/           # OpenAI provider & analysis schemas
│   │   ├── edgar/         # SEC filing integration (edgartools)
│   │   ├── cache/         # Redis multi-level caching
│   │   └── tasks/         # Celery background processing
│   ├── presentation/      # FastAPI REST API
│   │   └── api/
│   │       └── routers/   # 13+ API endpoints
│   └── shared/            # Cross-cutting concerns
├── tests/                 # 🧪 COMPREHENSIVE TESTING
│   ├── unit/             # Layer-specific unit tests
│   ├── integration/      # Cross-layer integration tests
│   ├── e2e/              # End-to-end workflow tests
│   └── fixtures/         # Realistic test data
├── docs/                 # 📚 PROJECT DOCUMENTATION
│   ├── phases/           # Development phase tracking
│   ├── architecture/     # Architecture decisions
│   └── implementation/   # Feature implementation summaries
└── scripts/              # Development & validation tools
```

## ⚡ Technology Stack

### 🎨 Frontend Technologies
- **Framework**: React 19 with React Compiler for optimal performance
- **Language**: TypeScript 5.7 with strict mode and comprehensive type checking
- **Build Tool**: Vite 6 (160ms dev server startup time)
- **Styling**: Tailwind CSS 4 with semantic design tokens and responsive design
- **State Management**:
  - **Client State**: Zustand for lightweight, type-safe state management
  - **Server State**: React Query (TanStack Query) for intelligent data fetching and caching
- **Charts & Visualization**: Recharts for interactive financial data visualization
- **Testing**: Vitest with React Testing Library (1,444+ tests, 85%+ coverage)
- **Type Safety**: Full TypeScript integration with auto-generated API types

### 🔧 Backend Technologies
- **Language**: Python 3.12 with strict type checking (MyPy 95%+ coverage)
- **Web Framework**: FastAPI with async/await support and automatic OpenAPI generation
- **Database**: PostgreSQL 16 with async SQLAlchemy 2.0+ ORM
- **Cache**: Redis 7 with multi-level caching and intelligent TTL strategies
- **Task Queue**: Celery with Redis broker for scalable background processing
- **API Documentation**: Auto-generated OpenAPI 3.0 specification with interactive docs

### 🏗️ Architecture & Patterns
- **Full-Stack Architecture**: Complete frontend + backend separation with REST API
- **Clean Architecture**: Domain-driven design with four distinct layers
- **CQRS Pattern**: Command/query separation with dedicated handlers
- **Repository Pattern**: Async data access with proper entity/model separation
- **Circuit Breaker**: Fault tolerance for external service integrations
- **Dependency Injection**: Constructor injection with interface-based abstractions

### 🔌 External Integrations
- **SEC Data**: edgartools library for direct SEC EDGAR database access
- **AI Analysis**: OpenAI GPT-4 with structured output schemas for financial insights
- **Background Processing**: Async task queues for long-running LLM analysis operations
- **Export Features**: PDF generation (WeasyPrint) and Excel exports (openpyxl)

### 🧪 Development & Quality
- **Testing Strategy**:
  - **Backend**: pytest with 85%+ coverage, async testing, realistic fixtures
  - **Frontend**: Vitest + React Testing Library with 85%+ coverage
  - **Integration**: End-to-end API and workflow testing
- **Type Safety**:
  - **Backend**: Strict MyPy with comprehensive type annotations
  - **Frontend**: TypeScript strict mode with auto-generated API types
- **Code Quality**:
  - **Backend**: Ruff linting, Black formatting, isort import organization
  - **Frontend**: ESLint, Prettier, TypeScript compiler checks
- **Security**: Bandit security scanning, dependency vulnerability checking
- **Infrastructure**: Docker & Docker Compose for development and production

### 🚀 Production Features
- **Performance**:
  - React 19 compiler optimizations for optimal rendering
  - Async-first backend architecture with connection pooling
  - Intelligent caching strategies at multiple levels
- **Scalability**:
  - Background task processing for heavy LLM analysis workloads
  - Horizontal scaling ready with stateless design
- **Monitoring**: Health endpoints, service status monitoring, and comprehensive logging
- **Reliability**: Circuit breaker patterns, comprehensive error handling, graceful degradation

## 🚀 Getting Started

### Prerequisites

**System Requirements:**
- **Python 3.12+** for backend development
- **Node.js 18+** for frontend development
- **Docker & Docker Compose** for services (PostgreSQL, Redis)
- **Poetry** for Python dependency management

### Quick Start (Full-Stack Setup)

**1. Clone and Setup**
```bash
git clone https://github.com/Dogecat0/Aperilex.git
cd aperilex
```

**2. Backend Setup**
```bash
# Install Python dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your OpenAI API key and other settings

# Start infrastructure services (PostgreSQL, Redis)
docker-compose up -d

# Run database migrations
alembic upgrade head
```

**3. Frontend Setup**
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Return to project root
cd ..
```

**4. Start the Application**

**Terminal: Frontend Application**
```bash
cd frontend
npm run dev
# Web app available at http://localhost:3000
```

**5. Verify Installation**
- **Web App**: Open http://localhost:3000 for the complete user interface

### Development Workflow

**Full-Stack Development:**
```bash
# Backend quality checks
poetry run mypy src/ && poetry run ruff check src/

# Frontend quality checks
cd frontend
npm run typecheck && npm run lint

# Run all tests
npm run test              # Frontend tests
cd .. && pytest         # Backend tests

# Auto-format code
poetry run black src/ && poetry run isort src/  # Backend
cd frontend && npm run format                   # Frontend
```

**Development Scripts:**
```bash
# Backend development
poetry run uvicorn src.presentation.api.app:app --reload

# Frontend development
cd frontend && npm run dev

# Run backend tests with coverage
pytest --cov=src --cov-report=html

# Run frontend tests with coverage
cd frontend && npm run test:coverage
```

## 💼 Use Cases

**For Individual Investors:**
- Research companies before making investment decisions
- Get plain-English explanations of complex SEC filings
- Track key financial metrics and trends over time
- Identify risks and opportunities in investment targets

**For Financial Analysts:**
- Streamline SEC filing analysis with AI-powered insights
- Generate comprehensive reports with export functionality
- Compare companies across industries and timeframes
- Access structured financial data through REST API

**For Students & Educators:**
- Learn financial analysis through interactive examples
- Understand SEC filing structures and content
- Practice financial research with real company data
- Export analysis results for assignments and presentations

**For Developers:**
- Integrate financial analysis into existing applications
- Build custom dashboards with comprehensive REST API
- Access structured SEC data with TypeScript support
- Leverage background processing for scalable analysis

## 🌟 Key Features in Detail

### 🔍 Smart Company Research
- **Universal Search**: Find companies by ticker symbol, name, or CIK number
- **Company Profiles**: Comprehensive company information with filing history
- **Recent Filings**: Quick access to latest 10-K, 10-Q, and 8-K filings
- **Analysis History**: Track all previous analyses and results

### 🤖 AI-Powered SEC Filing Analysis
- **Comprehensive Analysis**: Complete filing breakdown with executive summary
- **Section Analysis**: Detailed insights into business operations, financials, and risks
- **Plain-English Summaries**: Complex financial language translated for everyone
- **Confidence Scoring**: AI confidence levels for analysis reliability

### 📊 Interactive Data Visualization
- **Financial Charts**: Revenue, profit, and key metric trends over time
- **Risk Assessment**: Visual breakdown of risk factors and their impact
- **Comparative Analysis**: Side-by-side company comparisons
- **Export Options**: PDF reports and Excel spreadsheets with full data

### ⚡ Performance & Reliability
- **Background Processing**: Long-running analyses don't block the interface
- **Intelligent Caching**: Smart caching reduces API calls and improves speed
- **Fault Tolerance**: Circuit breaker patterns ensure system reliability
- **Real-time Updates**: WebSocket-like updates for analysis progress

## 🛠️ Development Features

### 🧪 Comprehensive Testing
- **Backend**: 85%+ test coverage with pytest, realistic fixtures, async testing
- **Frontend**: 85%+ test coverage with Vitest, React Testing Library, MSW mocking
- **Integration**: End-to-end API testing and workflow validation
- **Performance**: Load testing and performance benchmarking

### 📋 Quality Assurance
- **Type Safety**: 95%+ MyPy coverage, TypeScript strict mode throughout
- **Code Quality**: Automated formatting, linting, and style enforcement
- **Security Scanning**: Dependency vulnerability checking and security audits
- **Pre-commit Hooks**: Automated quality checks before every commit

### 🚀 Production Ready
- **Docker Deployment**: Complete containerization with docker-compose
- **Health Monitoring**: Service health endpoints and status monitoring
- **Error Handling**: Comprehensive error handling with proper logging
- **Scalability**: Horizontal scaling ready with stateless design

## API Endpoints (LIVE)

**Complete REST API implemented with 8 core endpoints:**

### Filing Analysis
```bash
# Trigger comprehensive filing analysis
POST /api/filings/{accession}/analyze
{
  "analysis_template": "COMPREHENSIVE",
  "sections": ["business", "financials", "risks", "mda"]
}

# Get filing details and metadata
GET /api/filings/{accession}

# Get analysis results for a filing
GET /api/filings/{accession}/analysis
```

### Analysis Management
```bash
# List all analyses with pagination and filtering
GET /api/analyses?page=1&limit=10&company_ticker=AAPL

# Get specific analysis by ID
GET /api/analyses/{analysis_id}

# Get available analysis templates
GET /api/analyses/templates
```

### Company Research
```bash
# Get company information by ticker
GET /api/companies/{ticker}

# Get all analyses for a company
GET /api/companies/{ticker}/analyses
```

## 🎯 Current Status

**Phase 5 COMPLETED (95%)**: Full-Stack Web Application
- ✅ **Complete React 19 Web Application** with 47+ components and responsive design
- ✅ **Interactive Dashboards** with real-time analysis progress and financial visualizations
- ✅ **Export Features** - PDF reports and Excel spreadsheet generation
- ✅ **Theme System** - Production-ready design system with Tailwind CSS 4
- ✅ **1,444+ Frontend Tests** with 85%+ coverage using Vitest and React Testing Library
- ✅ **TypeScript Integration** - Full type safety with auto-generated API clients
- ✅ **State Management** - Zustand + React Query for optimal performance
- ✅ **Financial Visualizations** - Interactive charts with Recharts for data analysis

**Backend Foundation (Phases 1-4) - COMPLETED**:
- ✅ **Complete CQRS Architecture** with 8 command/query handlers
- ✅ **REST API** with 13+ endpoints supporting full web application
- ✅ **EdgarTools Integration** - Complete SEC filing access with compliance
- ✅ **AI-Powered Analysis** - OpenAI GPT-4 with structured financial insights
- ✅ **Background Processing** - Celery task queues for scalable analysis operations
- ✅ **Multi-Level Caching** - Redis caching with intelligent TTL strategies
- ✅ **Comprehensive Testing** - 85%+ backend coverage with realistic fixtures

**✨ What's Working Right Now:**
1. **Complete Web Application**: Visit the React interface for intuitive financial analysis
2. **Company Research**: Search any public company and get AI-powered insights
3. **SEC Filing Analysis**: Analyze 10-K, 10-Q, and 8-K filings with plain-English summaries
4. **Interactive Dashboards**: Real-time progress tracking and analysis results visualization
5. **Export Capabilities**: Generate PDF reports and Excel spreadsheets
6. **Developer API**: Full REST API with OpenAPI documentation for integrations

**🚧 Final Phase (5-7 days to production)**: Authentication & Deployment
- Gmail OAuth integration for user accounts and email notifications
- Production SSL/TLS configuration and security hardening
- CI/CD pipeline setup with automated testing and deployment
- Final performance optimization and monitoring setup

**Production Readiness**: Aperilex is a **fully functional financial analysis platform** with both web interface and API ready for immediate use. The remaining work focuses on user authentication and production deployment infrastructure.

**🔗 Project Documentation**: See `docs/phases/` for detailed development history and architectural decisions.

## 🔒 Security

Aperilex implements comprehensive security measures:

- **Input Validation**: Pydantic schema validation for all API inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **Dependency Security**: Regular vulnerability scanning with Bandit and Safety
- **Container Security**: Docker security best practices
- **Rate Limiting**: API endpoint rate limiting (ready for production)
- **CORS Configuration**: Secure cross-origin resource sharing setup
- **Environment Security**: Proper secrets management and environment isolation

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

Copyright (c) 2024 Aperilex Contributors.

---
