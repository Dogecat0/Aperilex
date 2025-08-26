# Aperilex - AI-Powered Financial Analysis Platform (v2.0.0)

**Democratize financial analysis by making SEC filings as easy to understand as reading a news article.**

Aperilex is an open-source financial analysis platform that transforms complex SEC filings into clear, actionable insights. Whether you're an investor, analyst, student, or simply curious about public companies, Aperilex provides AI-powered analysis through an intuitive web interface and powerful developer API.

## 🔄 Current Status

**Version**: 2.0.0 - Production-Ready Architecture

**✅ Completed:**

- Clean Domain-Driven Design with CQRS pattern implementation
- Flexible messaging system with pluggable backends (local/RabbitMQ/AWS)
- Full-stack application with React 19 frontend and FastAPI backend
- Comprehensive API with OpenAPI documentation
- Multi-provider LLM support (OpenAI, Google AI)
- AWS deployment infrastructure with Pulumi

**🔧 Recent Updates:**

- Removed Redis/Celery dependencies for simplified architecture
- Implemented flexible messaging system for different deployment scenarios
- Added batch analysis capabilities for processing multiple filings
- Enhanced error handling with circuit breaker patterns
- Improved test coverage and code quality metrics

## 🚀 What Aperilex Does

**For Everyone:**

- **🔍 Smart Company Research**: Search any public company and get instant insights
- **📊 AI-Powered Analysis**: Automatic extraction of key risks, opportunities, and financial trends
- **📈 Interactive Dashboards**: Comprehensive analysis tracking with visual progress indicators
- **💾 Export & Sharing**: Generate PDF reports and JSON file of analysis results
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices

**For Developers:**

- **🔌 REST API**: FastAPI with automatic OpenAPI documentation and type safety
- **⚡ Flexible Processing**: Pluggable messaging backends (local, RabbitMQ, AWS SQS/Lambda)
- **📚 TypeScript Support**: Full type definitions with auto-generated API types

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
│          (Components, Dashboards, Visualizations)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API + TypeScript Client
┌───────────────────────────────▼─────────────────────────────────┐
│                      Presentation Layer                         │
│            FastAPI REST API with OpenAPI Documentation         │
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
│    (PostgreSQL + EdgarTools + OpenAI/Google AI + Messaging)    │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

**Full-Stack Application Structure:**

```
aperilex/
├── frontend/                # 🎨 REACT WEB APPLICATION
│   ├── src/
│   │   ├── components/      # React components
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
│   └── tests/              # Frontend test suite
├── src/                    # 🔧 BACKEND API
│   ├── domain/             # Business logic & entities
│   │   ├── entities/       # Analysis, Company, Filing
│   │   └── value_objects/  # Money, ProcessingStatus, Ticker
│   ├── application/        # CQRS application services
│   │   ├── commands/       # Command handlers (analysis orchestration)
│   │   ├── queries/        # Query handlers
│   │   ├── schemas/        # Pydantic DTOs & validation
│   │   ├── services/       # Application orchestrators
│   │   └── patterns/       # Circuit breaker, resilience
│   ├── infrastructure/     # External integrations
│   │   ├── database/       # PostgreSQL with SQLAlchemy
│   │   ├── repositories/   # Async repository pattern
│   │   ├── llm/           # OpenAI provider & analysis schemas
│   │   ├── edgar/         # SEC filing integration (edgartools)
│   │   ├── cache/         # Multi-level caching infrastructure
│   │   └── messaging/     # Flexible messaging (local/RabbitMQ/SQS)
│   ├── presentation/      # FastAPI REST API
│   │   └── api/
│   │       └── routers/   # API endpoints
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
├── scripts/              # 🔧 Development & deployment tools
│   ├── batch_analyze_filings.py  # Batch analysis for multiple filings
│   ├── import_snp500.sh          # S&P 500 company data import
│   ├── aws-entrypoint.sh         # AWS deployment entry point
│   └── reset_database.sh         # Database management utilities
└── pulumi/               # ☁️ Infrastructure as Code (AWS)
    ├── backend.py        # Backend Elastick Beanstalk configuration
    ├── frontend.py       # Frontend S3/CloudFront setup
    ├── database.py       # RDS PostgreSQL configuration
    └── orchestration.py  # AWS resource orchestration
```

## ⚡ Technology Stack

### 🎨 Frontend Technologies

- **Framework**: React 19 with React Compiler for optimal performance
- **Language**: TypeScript 5.7 with strict mode and comprehensive type checking
- **Build Tool**: Vite 6 for fast development and optimized production builds
- **Styling**: Tailwind CSS 4 with semantic design tokens and responsive design
- **State Management**:
  - **Client State**: Zustand for lightweight, type-safe state management
  - **Server State**: React Query (TanStack Query) for intelligent data fetching and caching
- **Charts & Visualization**: Recharts for interactive financial data visualization
- **Testing**: Vitest with React Testing Library for comprehensive component testing
- **Type Safety**: Full TypeScript integration with auto-generated API types

### 🔧 Backend Technologies

- **Language**: Python 3.12 with strict type checking via MyPy
- **Web Framework**: FastAPI with async/await support and automatic OpenAPI generation
- **Database**: PostgreSQL 16 with async SQLAlchemy 2.0+ ORM
- **Cache**: Multi-level caching with intelligent TTL strategies
- **Messaging**: Flexible messaging system with pluggable backends (local, RabbitMQ, AWS SQS)
- **Cloud Infrastructure**: AWS services (S3, RDS, ECS, CloudFront) via Pulumi IaC
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
- **AI Analysis**: Multiple LLM providers (OpenAI GPT-4, Google AI) with structured output schemas
- **Messaging System**: Pluggable backends - local (development), RabbitMQ (staging), AWS SQS/Lambda (production)
- **Storage**: Flexible storage backends - local filesystem, AWS S3

### 🧪 Development & Quality

- **Testing Strategy**:
  - **Backend**: pytest with comprehensive test coverage, async testing, realistic fixtures
  - **Frontend**: Vitest + React Testing Library for component and integration testing
  - **Integration**: End-to-end API and workflow testing
- **Type Safety**:
  - **Backend**: Strict MyPy with comprehensive type annotations
  - **Frontend**: TypeScript strict mode with auto-generated API types
- **Code Quality**:
  - **Backend**: Ruff linting, Black formatting, isort import organization
  - **Frontend**: ESLint, Prettier, TypeScript compiler checks
- **Security**: Bandit security scanning, dependency vulnerability checkingF
- **Infrastructure**: Docker & Docker Compose for development and production

### 🚀 Production Features

- **Performance**:
  - React 19 with optimized rendering and code splitting
  - Async-first backend with PostgreSQL connection pooling
  - Multi-level caching with configurable TTL strategies
- **Scalability**:
  - Pluggable messaging backends for different deployment scenarios
  - Stateless design enabling horizontal scaling
  - Support for AWS Lambda for serverless processing
- **Monitoring**:
  - Comprehensive health checks for all services
  - Structured logging with context propagation
  - OpenTelemetry instrumentation ready
- **Reliability**:
  - Circuit breaker patterns for external services
  - Graceful degradation when services are unavailable
  - Comprehensive error handling with retry logic

## 🚀 Getting Started

### Prerequisites

**System Requirements:**

- **Python 3.12+** for backend development
- **Node.js 18+** for frontend development
- **Docker & Docker Compose** for services (PostgreSQL)
- **Poetry** for Python dependency management
- **AWS CLI** (optional) for cloud deployment
- **Pulumi** (optional) for infrastructure as code

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

# Start infrastructure services (PostgreSQL)
docker-compose up -d postgres

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

**Quality Checks:**

```bash
# Backend quality checks
poetry run mypy src/
poetry run ruff check src/
poetry run black src/ --check

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

**Development Commands:**

```bash
# Start backend API server
poetry run uvicorn src.presentation.api.app:app --reload --port 8000

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

### ⚡ Performance & Reliability

- **Background Processing**: Long-running analyses don't block the interface
- **Intelligent Caching**: Smart caching reduces API calls and improves speed
- **Fault Tolerance**: Circuit breaker patterns ensure system reliability
- **Real-time Updates**: WebSocket-like updates for analysis progress

## 🛠️ Development Features

### 🧪 Comprehensive Testing

- **Backend**: High test coverage with pytest, realistic fixtures, async testing
- **Frontend**: Comprehensive test coverage with Vitest, React Testing Library, MSW mocking
- **Integration**: End-to-end API testing and workflow validation
- **Performance**: Load testing and performance benchmarking

### 📋 Quality Assurance

- **Type Safety**: Comprehensive MyPy coverage, TypeScript strict mode throughout
- **Code Quality**: Automated formatting, linting, and style enforcement
- **Security Scanning**: Dependency vulnerability checking and security audits
- **Pre-commit Hooks**: Automated quality checks before every commit

## API Endpoints

**Complete REST API with FastAPI backend:**

The API is organized into 5 main resource groups:

### 1. Filing Analysis (`/api/filings`)

### 2. Analysis Management (`/api/analyses`)

### 3. Company Research (`/api/companies`)

### 4. Task Management (`/api/tasks`)

### 5. Health Monitoring (`/api/health`)

**🔗 Project Documentation**: See `docs/phases/` for detailed development history and architectural decisions.

## 🚀 Deployment

### Deployment Options

#### Local Development

```bash
# Using Docker Compose
docker-compose up -d

# Access the application
# API: http://localhost:8000
# Frontend: http://localhost:3000
```

#### AWS Deployment (Production)

Aperilex includes complete infrastructure as code for AWS deployment using Pulumi:

**Infrastructure Components:**

- **Frontend**: S3 + CloudFront CDN for React application
- **Backend**: Elastic Beanstalk or Lambda for API services
- **Database**: RDS PostgreSQL with automated backups
- **Messaging**: SQS for task queues, Lambda for workers
- **Storage**: S3 for analysis results and file storage
- **Networking**: VPC with public/private subnets and security groups

**Deployment Steps:**

```bash
# Navigate to infrastructure directory
cd pulumi

# Install Pulumi dependencies
pip install -r requirements.txt

# Configure AWS credentials
export AWS_PROFILE=your-profile

# Deploy infrastructure
pulumi up --stack prod

# View deployment outputs
pulumi stack output
```

### Batch Processing

**Process Multiple SEC Filings:**

```bash
# Import S&P 500 companies to database
./scripts/import_snp500.sh

# Run batch analysis with concurrent processing
poetry run python scripts/batch_analyze_filings.py \
  --tickers AAPL,MSFT,GOOGL \
  --filing-type 10-K \
  --max-concurrent 5
```

**Available Scripts:**

- `batch_analyze_filings.py` - Process multiple company filings concurrently
- `import_snp500.sh` - Import S&P 500 company data
- `reset_database.sh` - Database management utilities
- `aws-entrypoint.sh` - AWS deployment entry point

## 🔒 Security

Aperilex implements comprehensive security measures:

- **Input Validation**: Pydantic schema validation for all API inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **Dependency Security**: Regular vulnerability scanning with Bandit and Safety
- **Container Security**: Docker security best practices
- **Rate Limiting**: API endpoint rate limiting (ready for production)
- **CORS Configuration**: Secure cross-origin resource sharing setup
- **Environment Security**: Proper secrets management and environment isolation

## 🔗 Resources

- **Documentation**: See `docs/` for architecture decisions and implementation details
- **API Documentation**: Available at `/docs` when running the API
- **Issues**: Report bugs and request features on GitHub
- **Contributing**: Contributions welcome! Please read contributing guidelines

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.
