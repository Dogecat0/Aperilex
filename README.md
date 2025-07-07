# Aperilex: Complete Project Rewrite Strategy

## Executive Summary

This document outlines a comprehensive rewrite strategy for the Aperilex SEC Filing Analysis Engine, addressing critical security vulnerabilities and architectural issues identified in the security analysis. The rewrite will transform a monolithic application with significant technical debt into a modern, secure, and maintainable system following best practices in software architecture and engineering.

## Current State Analysis

### Critical Issues Identified

1. **Security Vulnerabilities**

   - Exposed API keys in environment variables
   - No authentication/authorization system
   - Overly permissive CORS configuration
   - SQL injection vulnerabilities
   - Sensitive data exposure

2. **Architectural Problems**

   - Tight coupling with LLM providers
   - Synchronous processing bottlenecks
   - Poor separation of concerns
   - Inconsistent async patterns
   - No proper abstraction layers

3. **Code Quality Issues**
   - Large monolithic functions
   - Mixed business logic and infrastructure
   - Poor error handling
   - Limited test coverage
   - Magic numbers and hardcoded values

## Architecture Vision

### Design Principles

1. **Security First**: Every design decision prioritizes security
2. **Clean Architecture**: Clear separation between business logic and infrastructure
3. **Domain-Driven Design**: Rich domain models with encapsulated business rules
4. **Hexagonal Architecture**: Ports and adapters for external dependencies
5. **SOLID Principles**: Single responsibility, dependency inversion, etc.
6. **Event-Driven**: Asynchronous processing with event sourcing capabilities

### Target Architecture

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

## Implementation Strategy

### Phase 1: Foundation & Security (Week 1-2)

#### 1.1 Project Structure

```
aperilex/
├── src/
│   ├── domain/              # Business logic & entities
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── events/
│   │   ├── exceptions/
│   │   └── services/
│   ├── application/         # Use cases & DTOs
│   │   ├── commands/
│   │   ├── queries/
│   │   ├── handlers/
│   │   └── services/
│   ├── infrastructure/      # External services
│   │   ├── database/
│   │   ├── llm/
│   │   ├── sec_api/
│   │   ├── cache/
│   │   └── security/
│   ├── presentation/        # API & Web
│   │   ├── api/
│   │   ├── web/
│   │   └── middleware/
│   └── shared/             # Cross-cutting concerns
│       ├── config/
│       ├── logging/
│       └── monitoring/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
├── docker/
└── docs/
```

#### 1.2 Core Dependencies

```toml
[tool.poetry]
name = "aperilex"
version = "2.0.0"
description = "Secure SEC Filing Analysis Engine"

[tool.poetry.dependencies]
python = "^3.12"
# Web Framework
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
# Data Validation
pydantic = "^2.6.0"
pydantic-settings = "^2.2.0"
# Database
sqlalchemy = "^2.0.27"
alembic = "^1.13.1"
asyncpg = "^0.29.0"
# Security
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
cryptography = "^42.0.0"
# HTTP Client
httpx = "^0.26.0"
# Cache
redis = "^5.0.1"
# Task Queue
celery = {extras = ["redis"], version = "^5.3.6"}
# Monitoring
prometheus-client = "^0.20.0"
opentelemetry-api = "^1.22.0"
opentelemetry-instrumentation-fastapi = "^0.43b0"
# Logging
structlog = "^24.1.0"
# LLM
openai = "^1.12.0"
anthropic = "^0.18.0"
# Utilities
python-dateutil = "^2.8.2"
orjson = "^3.9.14"

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
hypothesis = "^6.98.0"
factory-boy = "^3.3.0"
# Code Quality
mypy = "^1.8.0"
ruff = "^0.2.0"
black = "^24.1.0"
isort = "^5.13.0"
# Security
bandit = "^1.7.7"
safety = "^3.0.0"
# Development
ipython = "^8.21.0"
rich = "^13.7.0"
pre-commit = "^3.6.0"
```

#### 1.3 Security Configuration

```python
# src/infrastructure/security/config.py
from pydantic import BaseSettings, SecretStr, validator
from cryptography.fernet import Fernet
import os

class SecuritySettings(BaseSettings):
    # JWT Settings
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: SecretStr

    # API Security
    api_key_header: str = "X-API-Key"
    rate_limit_per_minute: int = 60

    # CORS
    allowed_origins: list[str] = []

    @validator("secret_key", "encryption_key")
    def validate_keys(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError("Keys must be at least 32 characters")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

# src/infrastructure/security/encryption.py
class EncryptionService:
    def __init__(self, key: str):
        self.fernet = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        return self.fernet.decrypt(encrypted_data.encode()).decode()
```

### Phase 2: Domain Modeling (Week 3-4)

#### 2.1 Core Entities

```python
# src/domain/entities/company.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Company:
    """Company entity with business rules."""
    ticker: str
    name: str
    cik: str
    sector: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self._validate()

    def _validate(self):
        if not self.ticker or len(self.ticker) > 10:
            raise ValueError("Invalid ticker symbol")
        if not self.cik or not self.cik.isdigit():
            raise ValueError("CIK must be numeric")
        if len(self.cik) != 10:
            self.cik = self.cik.zfill(10)

# src/domain/entities/filing.py
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional
import uuid

class FilingType(str, Enum):
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"

    @property
    def is_periodic(self) -> bool:
        return self in (FilingType.FORM_10K, FilingType.FORM_10Q)

@dataclass
class Filing:
    """SEC filing entity."""
    id: uuid.UUID
    company_id: uuid.UUID
    filing_type: FilingType
    filing_date: date
    period_end_date: date
    accession_number: str
    document_url: str

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.filing_date > date.today():
            raise ValueError("Filing date cannot be in the future")
        if self.period_end_date > self.filing_date:
            raise ValueError("Period end date cannot be after filing date")

    @property
    def is_annual(self) -> bool:
        return self.filing_type == FilingType.FORM_10K

    @property
    def fiscal_period(self) -> str:
        if self.is_annual:
            return f"FY{self.period_end_date.year}"
        else:
            quarter = (self.period_end_date.month - 1) // 3 + 1
            return f"Q{quarter} {self.period_end_date.year}"
```

#### 2.2 Value Objects

```python
# src/domain/value_objects/analysis_result.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json

@dataclass(frozen=True)
class AnalysisResult:
    """Immutable analysis result value object."""
    content: Dict[str, Any]
    confidence_score: float
    model_used: str
    prompt_version: str
    processing_time_ms: int
    token_usage: Dict[str, int]
    cost_usd: float
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())
        self._validate()

    def _validate(self):
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")
        if self.cost_usd < 0:
            raise ValueError("Cost cannot be negative")

    @property
    def content_hash(self) -> str:
        """Generate hash of content for caching."""
        content_str = json.dumps(self.content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

# src/domain/value_objects/money.py
@dataclass(frozen=True)
class Money:
    """Money value object with currency support."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.currency not in ["USD", "EUR", "GBP"]:
            raise ValueError(f"Unsupported currency: {self.currency}")

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: float) -> 'Money':
        return Money(self.amount * Decimal(str(factor)), self.currency)
```

#### 2.3 Domain Events

```python
# src/domain/events/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import uuid

@dataclass
class DomainEvent:
    """Base domain event."""
    event_id: uuid.UUID = None
    occurred_at: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = uuid.uuid4()
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

# src/domain/events/filing_events.py
@dataclass
class FilingAnalysisRequested(DomainEvent):
    """Event raised when filing analysis is requested."""
    filing_id: uuid.UUID
    analysis_types: list[str]
    requested_by: str

@dataclass
class FilingAnalysisCompleted(DomainEvent):
    """Event raised when filing analysis is completed."""
    filing_id: uuid.UUID
    analysis_id: uuid.UUID
    analysis_type: str
    success: bool
    error_message: Optional[str] = None
```

### Phase 3: Application Layer (Week 5-6)

#### 3.1 Use Cases

```python
# src/application/commands/analyze_filing.py
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class AnalyzeFilingCommand:
    """Command to analyze a filing."""
    ticker: str
    filing_type: str
    analysis_types: list[str]
    filing_date: Optional[date] = None
    user_id: Optional[uuid.UUID] = None

# src/application/handlers/analyze_filing_handler.py
from typing import Protocol
import structlog

logger = structlog.get_logger()

class FilingRepository(Protocol):
    async def get_by_ticker_and_type(
        self, ticker: str, filing_type: str, filing_date: Optional[date]
    ) -> Optional[Filing]: ...

    async def save(self, filing: Filing) -> Filing: ...

class AnalysisRepository(Protocol):
    async def get_by_filing_id(
        self, filing_id: uuid.UUID, analysis_type: str
    ) -> Optional[Analysis]: ...

    async def save(self, analysis: Analysis) -> Analysis: ...

class LLMService(Protocol):
    async def analyze(
        self, content: str, analysis_type: str
    ) -> tuple[AnalysisResult, Money]: ...

class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

class AnalyzeFilingHandler:
    """Handler for filing analysis use case."""

    def __init__(
        self,
        filing_repo: FilingRepository,
        analysis_repo: AnalysisRepository,
        llm_service: LLMService,
        event_bus: EventBus,
        sec_service: SECDataService
    ):
        self.filing_repo = filing_repo
        self.analysis_repo = analysis_repo
        self.llm_service = llm_service
        self.event_bus = event_bus
        self.sec_service = sec_service

    async def handle(self, command: AnalyzeFilingCommand) -> AnalysisResponse:
        """Execute filing analysis."""
        # 1. Validate command
        self._validate_command(command)

        # 2. Get or fetch filing
        filing = await self._get_or_fetch_filing(command)

        # 3. Publish event
        await self.event_bus.publish(
            FilingAnalysisRequested(
                filing_id=filing.id,
                analysis_types=command.analysis_types,
                requested_by=str(command.user_id)
            )
        )

        # 4. Process each analysis type
        results = []
        total_cost = Money(Decimal("0"), "USD")

        for analysis_type in command.analysis_types:
            # Check cache
            existing = await self.analysis_repo.get_by_filing_id(
                filing.id, analysis_type
            )

            if existing and not self._is_stale(existing):
                results.append(existing)
                logger.info(
                    "using_cached_analysis",
                    filing_id=filing.id,
                    analysis_type=analysis_type
                )
                continue

            # Perform new analysis
            try:
                result, cost = await self._perform_analysis(
                    filing, analysis_type
                )
                results.append(result)
                total_cost += cost

                # Publish success event
                await self.event_bus.publish(
                    FilingAnalysisCompleted(
                        filing_id=filing.id,
                        analysis_id=result.id,
                        analysis_type=analysis_type,
                        success=True
                    )
                )

            except Exception as e:
                logger.error(
                    "analysis_failed",
                    filing_id=filing.id,
                    analysis_type=analysis_type,
                    error=str(e)
                )

                # Publish failure event
                await self.event_bus.publish(
                    FilingAnalysisCompleted(
                        filing_id=filing.id,
                        analysis_id=uuid.uuid4(),
                        analysis_type=analysis_type,
                        success=False,
                        error_message=str(e)
                    )
                )
                raise

        return AnalysisResponse(
            filing_id=filing.id,
            analyses=results,
            total_cost=total_cost
        )
```

#### 3.2 Query Handlers

```python
# src/application/queries/get_analysis_history.py
@dataclass
class GetAnalysisHistoryQuery:
    ticker: str
    limit: int = 10
    offset: int = 0

class GetAnalysisHistoryHandler:
    def __init__(self, read_model: AnalysisReadModel):
        self.read_model = read_model

    async def handle(
        self, query: GetAnalysisHistoryQuery
    ) -> list[AnalysisHistoryItem]:
        return await self.read_model.get_history(
            ticker=query.ticker,
            limit=query.limit,
            offset=query.offset
        )
```

### Phase 4: Infrastructure Layer (Week 7-8)

#### 4.1 Database Implementation

```python
# src/infrastructure/database/models.py
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()

class CompanyModel(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    sector = Column(String(100))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    filings = relationship("FilingModel", back_populates="company")

class FilingModel(Base):
    __tablename__ = "filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    filing_type = Column(String(10), nullable=False)
    filing_date = Column(DateTime, nullable=False)
    period_end_date = Column(DateTime, nullable=False)
    accession_number = Column(String(25), unique=True, nullable=False)
    document_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False)

    company = relationship("CompanyModel", back_populates="filings")
    analyses = relationship("AnalysisModel", back_populates="filing")

    __table_args__ = (
        Index("idx_filing_lookup", "company_id", "filing_type", "filing_date"),
    )

# src/infrastructure/database/repositories.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

class SQLFilingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_ticker_and_type(
        self, ticker: str, filing_type: str, filing_date: Optional[date]
    ) -> Optional[Filing]:
        query = (
            select(FilingModel)
            .join(CompanyModel)
            .where(
                and_(
                    CompanyModel.ticker == ticker,
                    FilingModel.filing_type == filing_type
                )
            )
        )

        if filing_date:
            query = query.where(FilingModel.filing_date == filing_date)
        else:
            query = query.order_by(FilingModel.filing_date.desc()).limit(1)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    def _to_entity(self, model: FilingModel) -> Filing:
        return Filing(
            id=model.id,
            company_id=model.company_id,
            filing_type=FilingType(model.filing_type),
            filing_date=model.filing_date,
            period_end_date=model.period_end_date,
            accession_number=model.accession_number,
            document_url=model.document_url
        )
```

#### 4.2 LLM Provider Abstraction

```python
# src/infrastructure/llm/base.py
from abc import ABC, abstractmethod
from typing import Protocol

class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[type] = None
    ) -> LLMResponse: ...

# src/infrastructure/llm/openai_provider.py
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, organization: Optional[str] = None):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            organization=organization
        )
        self._cost_calculator = OpenAICostCalculator()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def complete(
        self,
        prompt: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[type] = None
    ) -> LLMResponse:
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }

            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            if response_format:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)

            usage = response.usage.model_dump()
            cost = self._cost_calculator.calculate(model, usage)

            return LLMResponse(
                content=response.choices[0].message.content,
                model=model,
                usage=usage,
                cost=Money(Decimal(str(cost)), "USD"),
                raw_response=response
            )

        except openai.APIError as e:
            logger.error("openai_api_error", error=str(e), model=model)
            raise LLMProviderError(f"OpenAI API error: {str(e)}")

# src/infrastructure/llm/factory.py
class LLMProviderFactory:
    @staticmethod
    def create(provider_type: str, config: dict) -> LLMProvider:
        providers = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "azure": AzureOpenAIProvider
        }

        if provider_type not in providers:
            raise ValueError(f"Unknown provider: {provider_type}")

        return providers[provider_type](**config)
```

#### 4.3 Caching Layer

```python
# src/infrastructure/cache/redis_cache.py
import redis.asyncio as redis
import json
from typing import Optional, Any

class RedisCache:
    def __init__(self, url: str, ttl_seconds: int = 3600):
        self.redis = redis.from_url(url)
        self.ttl = ttl_seconds

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.redis.setex(
            key,
            ttl or self.ttl,
            json.dumps(value, default=str)
        )

    async def delete(self, key: str):
        await self.redis.delete(key)

    def make_key(self, *parts: str) -> str:
        return ":".join(["aperilex"] + list(parts))

# src/infrastructure/cache/cached_llm_service.py
class CachedLLMService:
    def __init__(self, llm_service: LLMService, cache: RedisCache):
        self.llm_service = llm_service
        self.cache = cache

    async def analyze(
        self, content: str, analysis_type: str
    ) -> tuple[AnalysisResult, Money]:
        # Generate cache key
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        cache_key = self.cache.make_key(
            "analysis", analysis_type, content_hash
        )

        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("cache_hit", key=cache_key)
            return (
                AnalysisResult(**cached["result"]),
                Money(Decimal(cached["cost"]["amount"]), cached["cost"]["currency"])
            )

        # Perform analysis
        result, cost = await self.llm_service.analyze(content, analysis_type)

        # Cache result
        await self.cache.set(
            cache_key,
            {
                "result": asdict(result),
                "cost": {"amount": str(cost.amount), "currency": cost.currency}
            },
            ttl=86400  # 24 hours
        )

        return result, cost
```

### Phase 5: API Layer (Week 9-10)

#### 5.1 FastAPI Application

```python
# src/presentation/api/app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from src.presentation.api.middleware import (
    SecurityMiddleware,
    RateLimitMiddleware,
    LoggingMiddleware,
    ErrorHandlerMiddleware
)
from src.presentation.api.routers import auth, analysis, health
from src.shared.config import get_settings

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    settings = get_settings()
    logger.info("starting_application", version=settings.version)

    # Initialize services
    await initialize_database()
    await initialize_cache()

    yield

    # Cleanup
    await shutdown_services()
    logger.info("application_stopped")

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Aperilex API",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None
    )

    # Middleware
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # CORS (restrictive)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600
    )

    # Routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(
        analysis.router,
        prefix="/api/v1/analysis",
        tags=["analysis"],
        dependencies=[Depends(require_auth)]
    )

    return app

# src/presentation/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return User(id=user_id, email=payload.get("email"))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

#### 5.2 API Endpoints

```python
# src/presentation/api/routers/analysis.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Annotated

router = APIRouter()

@router.post(
    "/filings/{ticker}",
    response_model=AnalysisResponseDTO,
    status_code=status.HTTP_201_CREATED
)
async def analyze_filing(
    ticker: str,
    request: AnalysisRequestDTO,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    handler: Annotated[AnalyzeFilingHandler, Depends(get_analysis_handler)]
):
    """Analyze SEC filing for a company."""
    try:
        # Validate ticker
        ticker = ticker.upper()
        if not re.match(r"^[A-Z]{1,10}$", ticker):
            raise HTTPException(
                status_code=400,
                detail="Invalid ticker symbol"
            )

        # Create command
        command = AnalyzeFilingCommand(
            ticker=ticker,
            filing_type=request.filing_type,
            analysis_types=request.analysis_types,
            filing_date=request.filing_date,
            user_id=current_user.id
        )

        # Execute handler
        result = await handler.handle(command)

        # Queue background tasks if needed
        if request.send_notification:
            background_tasks.add_task(
                send_completion_notification,
                user_id=current_user.id,
                filing_id=result.filing_id
            )

        return AnalysisResponseDTO.from_domain(result)

    except ValidationError as e:
        logger.warning("validation_error", error=str(e), ticker=ticker)
        raise HTTPException(status_code=400, detail=str(e))
    except FilingNotFoundError as e:
        logger.warning("filing_not_found", ticker=ticker)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("analysis_error", error=str(e), ticker=ticker)
        raise HTTPException(status_code=500, detail="Analysis failed")

@router.get(
    "/history/{ticker}",
    response_model=list[AnalysisHistoryItemDTO]
)
async def get_analysis_history(
    ticker: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Annotated[User, Depends(get_current_user)],
    handler: Annotated[GetAnalysisHistoryHandler, Depends()]
):
    """Get analysis history for a company."""
    query = GetAnalysisHistoryQuery(
        ticker=ticker.upper(),
        limit=limit,
        offset=offset
    )

    results = await handler.handle(query)
    return [AnalysisHistoryItemDTO.from_domain(r) for r in results]
```

### Phase 6: Testing & Quality (Week 11-12)

#### 6.1 Unit Testing

```python
# tests/unit/domain/test_filing.py
import pytest
from datetime import date
from src.domain.entities import Filing, FilingType

class TestFiling:
    def test_create_valid_filing(self):
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2024, 3, 1),
            period_end_date=date(2023, 12, 31),
            accession_number="0001234567890123456",
            document_url="https://sec.gov/..."
        )

        assert filing.is_annual
        assert filing.fiscal_period == "FY2023"

    def test_invalid_future_filing_date(self):
        with pytest.raises(ValueError, match="future"):
            Filing(
                id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2025, 1, 1),
                period_end_date=date(2023, 12, 31),
                accession_number="0001234567890123456",
                document_url="https://sec.gov/..."
            )

# tests/unit/infrastructure/test_llm_provider.py
@pytest.mark.asyncio
async def test_openai_provider_retry_on_error(mocker):
    # Arrange
    mock_client = mocker.Mock()
    mock_client.chat.completions.create = mocker.AsyncMock(
        side_effect=[
            openai.APIError("Temporary error"),
            mocker.Mock(
                choices=[mocker.Mock(message=mocker.Mock(content="Success"))],
                usage=mocker.Mock(
                    model_dump=lambda: {
                        "prompt_tokens": 10,
                        "completion_tokens": 20
                    }
                )
            )
        ]
    )

    provider = OpenAIProvider(api_key="test")
    provider.client = mock_client

    # Act
    result = await provider.complete("Test prompt")

    # Assert
    assert result.content == "Success"
    assert mock_client.chat.completions.create.call_count == 2
```

#### 6.2 Integration Testing

```python
# tests/integration/test_analysis_flow.py
@pytest.mark.asyncio
async def test_complete_analysis_flow(
    test_db,
    test_cache,
    mock_llm_provider,
    mock_sec_service
):
    # Arrange
    async with test_db.session() as session:
        # Create test data
        company = CompanyModel(
            ticker="AAPL",
            name="Apple Inc.",
            cik="0000320193"
        )
        session.add(company)
        await session.commit()

        # Setup mocks
        mock_sec_service.fetch_filing.return_value = Filing(...)
        mock_llm_provider.complete.return_value = LLMResponse(
            content='{"segments": ["iPhone", "Mac"]}',
            model="gpt-4",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            cost=Money(Decimal("0.01"), "USD")
        )

        # Create handler
        handler = AnalyzeFilingHandler(
            filing_repo=SQLFilingRepository(session),
            analysis_repo=SQLAnalysisRepository(session),
            llm_service=LLMAnalysisService(mock_llm_provider),
            event_bus=InMemoryEventBus(),
            sec_service=mock_sec_service
        )

        # Act
        command = AnalyzeFilingCommand(
            ticker="AAPL",
            filing_type="10-K",
            analysis_types=["business"]
        )

        result = await handler.handle(command)

        # Assert
        assert result.filing_id is not None
        assert len(result.analyses) == 1
        assert result.total_cost.amount > 0

        # Verify database
        analysis = await session.get(AnalysisModel, result.analyses[0].id)
        assert analysis is not None
        assert analysis.status == "completed"
```

#### 6.3 Performance Testing

```python
# tests/performance/test_load.py
import asyncio
from locust import HttpUser, task, between

class AnalysisUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Authenticate
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass"}
        )
        self.token = response.json()["access_token"]

    @task(weight=3)
    def analyze_filing(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.post(
            "/api/v1/analysis/filings/AAPL",
            headers=headers,
            json={
                "filing_type": "10-K",
                "analysis_types": ["business", "risks"]
            }
        )

    @task(weight=1)
    def get_history(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get(
            "/api/v1/analysis/history/AAPL",
            headers=headers
        )
```

## Deployment Strategy

### Local Development

```yaml
# docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: aperilex
      POSTGRES_USER: aperilex
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://aperilex:${DB_PASSWORD}@postgres/aperilex
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./src:/app/src
    command: uvicorn src.presentation.api.app:app --reload --host 0.0.0.0

volumes:
  postgres_data:
```

### Production Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Runtime stage
FROM python:3.12-slim

# Security: Create non-root user
RUN useradd -m -u 1000 appuser

# Copy dependencies
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
WORKDIR /app
COPY --chown=appuser:appuser . .

# Security: Run as non-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Run application
EXPOSE 8000
CMD ["uvicorn", "src.presentation.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Security Checklist

- [ ] All API endpoints require authentication
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention via ORM
- [ ] XSS prevention in responses
- [ ] CSRF protection
- [ ] Secrets encrypted at rest
- [ ] TLS/HTTPS only
- [ ] Security headers configured
- [ ] Regular dependency updates
- [ ] Vulnerability scanning in CI/CD
- [ ] Audit logging enabled
- [ ] Data encryption for PII
- [ ] Secure password storage (bcrypt)
- [ ] JWT token expiration

## Monitoring & Observability

```python
# src/shared/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status']
)

llm_cost_total = Counter(
    'llm_cost_total_usd',
    'Total LLM API cost in USD',
    ['provider', 'model']
)

active_analyses = Gauge(
    'active_analyses',
    'Number of active analyses'
)
```

## Conclusion

This comprehensive rewrite strategy addresses all critical issues identified in the security analysis while establishing a foundation for a maintainable, secure, and scalable application. The implementation follows best practices in software architecture, emphasizing:

1. **Security**: Authentication, authorization, encryption, and input validation
2. **Clean Architecture**: Clear separation of concerns with hexagonal architecture
3. **Domain-Driven Design**: Rich domain models with encapsulated business logic
4. **Testability**: Comprehensive testing strategy with high coverage
5. **Observability**: Metrics, logging, and monitoring for production readiness

The 12-week timeline provides a realistic path for a solo developer to implement this system while learning and applying best practices throughout the journey.
