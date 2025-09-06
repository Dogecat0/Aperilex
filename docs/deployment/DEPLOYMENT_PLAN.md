# Aperilex AWS Deployment Plan

## Architecture Overview

### Core Principles

- **SIMPLE**: Minimal moving parts, easy to understand and maintain
- **FUNCTIONAL**: Covers all core requirements for startup launch
- **NOT OVER ENGINEERED**: No premature optimization or complex patterns
- **EXTREMELY LOW COST**: Optimized for startup budget (~$25-45/month including domain & IP)
- **MODULAR INTERFACES**: Abstract all external services for flexibility
- **PROVIDER AGNOSTIC**: Easy switching between cloud/local implementations

### Selected AWS Services

```table
Frontend:          S3 + CloudFront (Static hosting + CDN)
API Orchestrator:  Elastic Beanstalk (t3.micro instance: 2 vCPU, 1GB RAM)
Public Access:     Elastic IP (initially) → ALB (when scaling)
Task Queue:        SQS FIFO (Message deduplication + ordering)
Workers:           AWS Lambda (Auto-scaling, pay-per-execution)
Database:          Aurora Serverless v2 (0 ACU minimum, true scale-to-zero)
                   Alternative: CockroachDB Serverless (AWS Marketplace)
Storage:           S3 (File storage, global analysis pool)
DNS/SSL:           Route 53 + ACM (free SSL certificates)
Domain:            .com domain via Route 53 Domains
```

**Upgrade Path**: Add Application Load Balancer when scaling to multiple instances

## Technical Interfaces & Abstractions

### Type System Overview

The system employs strict typing throughout with a comprehensive type hierarchy using Pydantic models for validation.

**Method Parameter Convention**: Methods with more than 3-4 parameters should accept a single Pydantic model object instead of individual arguments for better readability and validation. For example, instead of `complete(prompt, system_prompt, temperature, max_tokens, ...)`, use `complete(request: LLMRequest)`.

#### Provider Enums

All external service integrations use enum-based provider selection:

- **Storage**: `S3`, `LOCAL`, `GCS`, `AZURE_BLOB`
- **Queue**: `SQS`, `RABBITMQ`, `PUBSUB`, `SERVICE_BUS`
- **Worker**: `LAMBDA`, `DOCKER`, `CLOUD_RUN`, `CONTAINER_INSTANCES`
- **Data Source**: `EDGAR`, `REFINITIV`, `BLOOMBERG`, `CUSTOM_API`
- **LLM**: `OPENAI`, `BEDROCK`, `VERTEX_AI`, `AZURE_OPENAI`, `ANTHROPIC`, `OLLAMA`
- **Database**: `POSTGRES`, `AURORA`, `MYSQL`, `SQLSERVER`

#### Entity Identifiers

All entities use UUID-based types for compile-time safety:

- `TaskId`, `FilingId`, `AnalysisId`, `UserId`, `CompanyId` → UUID
- `StorageKey`, `QueueMessageId`, `ReceiptHandle` → String-based service identifiers

#### Domain Types

Validated value objects ensure data integrity (Pydantic models with validators):

- **Email**: Validated email addresses with @ symbol requirement
- **Ticker**: 1-5 character alphanumeric stock symbols
- **CIK**: 10-digit SEC Central Index Key

#### Status Enums

- **TaskStatus**: 7 states (`PENDING` → `COMPLETED`/`FAILED`/`CANCELLED`)
- **AnalysisStatus**: 8 states tracking full lifecycle (`INITIATED` → `COMPLETED`/`ERROR`)
- **FilingType**: SEC form types (`10-K`, `10-Q`, `8-K`, `20-F`, `DEF-14A`, `S-1`)
- **TaskPriority**: 5 levels (`CRITICAL=0` → `BACKGROUND=9`)
- **UserTier**: `DEMO`, `BASIC`, `PROFESSIONAL`, `ENTERPRISE`

### Storage Service Interface

**Purpose**: Abstracts file storage operations across cloud and local providers

**Interface Versioning**:

- `interface_version: int = 1` in all requests/responses
- Version negotiation on service initialization
- Full backward compatibility for all previous versions
- Deprecation warnings after 3+ major versions
- Breaking changes only when absolutely necessary

**Core Operations**:

- Store filing: `store_filing(request: StorageRequest)` → `StorageKey`
- Retrieve filing: `get_filing(filing_id: FilingId)` → `bytes`
- Store analysis: `store_analysis(request: AnalysisStorageRequest)` → `StorageKey`
- Retrieve analysis: `get_analysis(analysis_id: AnalysisId)` → `AnalysisResult`
- Check existence and delete items
- All operations use UUID-based identifiers
- Optional: Query capabilities (S3 Select, Athena) with fallback to full scan

**Request/Response Models**:

- `StorageRequest` (v1): Filing ID, content, metadata, schema version
- `AnalysisStorageRequest` (v1): Analysis ID, result, metadata, schema version
- **Future**: v2 for new metadata fields, v3 for new storage formats

**Provider Implementations**:

- **S3**: AWS S3 (encryption, lifecycle, replication handled by IaC)
- **Local**: Filesystem-based for development/testing
- **Future**: Google Cloud Storage, Azure Blob Storage

**Note**: All document data (filings, analysis results) stored here, not in relational database

### Core Data Models

All data models use **Pydantic BaseModel** for automatic validation, serialization, and type coercion.

**Schema Versioning Strategy**:

- All models include `schema_version: int` field
- Version incremented for any structural changes
- Full backward compatibility maintained indefinitely
- Version handlers/converters for each schema version
- Deprecation warnings logged after 5+ versions
- Tasks only fail for corrupted/unparseable data

**Task Data Structure** (Pydantic model):

- `schema_version: int = 1` (for future task type expansion)
- `TaskId` (UUID): Unique task identifier
- `FilingId` (UUID): Reference to filing being analyzed
- `UserId` (UUID): User requesting analysis
- `Email`: Validated email for notifications
- `Ticker`: Stock symbol (1-5 alphanumeric chars)
- `FilingType`: SEC form type enum
- `TaskPriority`: 0-9 priority level
- Includes retry count, metadata, and deduplication ID
- **Future versions**: v2 for batch analysis, v3 for comparison tasks

**Analysis Models** (Pydantic models):

- `AnalysisRequest` (v1): Basic single-filing analysis
  - `schema_version: int = 1`
  - Tracks analysis parameters (LLM provider, model, type)
  - **Future**: v2 for multi-filing, v3 for custom prompts
- `AnalysisResult` (v1): Standard analysis output
  - `schema_version: int = 1`
  - Contains LLM response, tokens used, cost, processing time
  - **Future**: v2 with structured extraction, v3 with charts/visualizations

**Queue Message Structure** (Pydantic model):

- `schema_version: int = 1`
- Wraps TaskData with queue-specific metadata
- Includes receipt handle for acknowledgment
- Tracks receive count for retry logic
- **Future**: v2 for priority lanes, v3 for batch messages

### Queue Service Interface

**Purpose**: Abstracts message queue operations for task distribution

**Core Operations**:

- Send task: `send_task(task: TaskData)` → `QueueMessageId`
- Receive tasks: `receive_tasks(request: ReceiveRequest)` → `List[QueueMessage]`
- Delete task: `delete_task(receipt_handle: ReceiptHandle)` → `bool`
- Adjust visibility: `change_visibility(request: VisibilityRequest)` → `bool`
- Monitor queue depth: `get_queue_depth()` → `int`

**Deduplication Strategy**:

- Maximum deduplication window allowed by provider
- Key: `{filing_id}_{user_email}`
- SQS FIFO: Built-in deduplication (5-minute maximum)
- RabbitMQ: Custom deduplication with cache/database (configurable window)

### LLM Provider Interface

**Purpose**: Generic interface for multiple LLM providers

**Configuration** (Pydantic models):

- Provider selection via enum (OpenAI, Bedrock, Vertex AI, Azure, Anthropic, Ollama)
- Model-specific parameters (temperature, max_tokens, penalties)
- Timeout and retry configuration
- API keys from environment variables

**Request/Response Types** (Pydantic models):

- `LLMRequest`: Prompt, system prompt, response format, streaming option, model tier
- `LLMResponse`: Content, token counts, latency, cost calculation, model used

**Core Operations**:

- Complete: `complete(request: LLMRequest)` → `LLMResponse`
- Complete with retry: `complete_with_retry(request: LLMRequest)` → `LLMResponse`
- Stream: `stream_complete(request: LLMRequest)` → `AsyncIterator[str]`
- Estimate tokens: `estimate_tokens(text: str)` → `int`
- Estimate cost: `estimate_cost(request: CostEstimateRequest)` → `float`

**Provider Implementations**:

- **OpenAI**: GPT-4, GPT-3.5 models
- **Bedrock**: Nova Lite (ultra-low cost), Claude models
- **Vertex AI**: Gemini models
- **Local**: Ollama for development/testing

### Worker Service Interface

**Purpose**: Abstracts worker execution environments

**Configuration** (Pydantic models):

- Provider selection (Lambda, Docker, Cloud Run, Container Instances)
- Resource limits (memory, CPU, timeout)
- Concurrency and environment settings

**Worker Context** (Pydantic model):

- Task tracking with correlation ID
- Deadline management
- Retry count and metadata

**Processing Workflow**:
Workers receive `TaskData` (v1) and `WorkerContext` (v1) models:

1. **Version Check**: Validate task schema version, handle upgrade if needed
2. **Filing Check**: Query database for existing filing
3. **Filing Fetch**: If not exists, fetch from EDGAR using `FilingRequest` (v1)
4. **Storage**: Store filing using `StorageRequest` (v1)
5. **LLM Analysis**: Send `LLMRequest` (v1) to provider
6. **Result Storage**: Store analysis using `AnalysisStorageRequest` (v1)
7. **Database Update**: Update using `StatusUpdateRequest` (v1)
8. **Event Publishing**: Send completion event to SNS/SQS for SSE notification
9. **Return**: `TaskResult` (v1) with completion status

**Version Handling**:

- Workers support all previous schema versions (full backward compatibility)
- Automatic migration/adaptation for older schema versions
- Deprecation warnings for very old versions (but still process)
- Only fail task if schema is fundamentally incompatible
- Version converters maintained for each schema evolution

**Error Handling**:

- Automatic retry with exponential backoff
- Dead letter queue for failed tasks
- Detailed error logging and tracking

**Provider Implementations**:

- **Lambda**: Serverless, auto-scaling, 15-min max timeout
- **Docker**: Local development, full control
- **Future**: Cloud Run, Azure Container Instances

### Data Source Interface

**Purpose**: Abstracts filing data retrieval from multiple sources

**Data Structures** (Pydantic models):

- `CompanyInfo`: Company details (name, ticker, CIK, industry, market cap)
- `FilingContent`: Raw HTML/text, parsed sections, tables, exhibits
- `SearchQuery`: Multi-criteria search parameters with validation

**Core Operations**:

- Fetch filing: `fetch_filing(request: FilingRequest)` → `FilingContent`
- Fetch by URL: `fetch_filing_by_url(url: str)` → `FilingContent`
- Search: `search_filings(query: SearchQuery)` → `List[FilingMetadata]`
- Company info: `get_company_info(ticker: Ticker)` → `CompanyInfo`
- Latest filing: `get_latest_filing(request: LatestFilingRequest)` → `Optional[FilingMetadata]`

**Provider Implementations**:

- **EDGAR**: SEC's official filing system
- **Future**: Refinitiv, Bloomberg, custom APIs

**Filing Processing**:

- HTML parsing and text extraction
- Section identification (Risk Factors, MD&A, etc.)
- Table extraction and structuring
- Exhibit linking and metadata

### Database Service Interface

**Purpose**: Persistent storage for metadata and state management

**Provider Options**:

- **Postgres**: Primary relational database for development
- **Aurora Serverless v2**: Production option with true scale-to-zero
  - Scales down to 0 ACU (no minimum charges)
  - Pay per ACU-second of actual usage
  - Postgres or MySQL compatible
- **CockroachDB Serverless**: Alternative from AWS Marketplace
  - True scale-to-zero (no minimum cost)
  - Pay-per-request pricing model
  - Postgres-compatible wire protocol
  - Built-in global replication
- **MySQL**: Alternative relational database option
- **All providers use relational model** - documents stored in object storage only

**Database Pricing Comparison**:

- **Aurora Serverless v2**: Charges per ACU-second when running (scales to 0)
- **CockroachDB Serverless**: Charges per request/operation
- Both offer true $0 when idle, different pricing models when active
- Aurora better for sustained load, CockroachDB better for sporadic requests
- Both fully compatible with SQLAlchemy/Alembic

**ORM & Migration Strategy**:

- **ORM**: SQLAlchemy for database abstraction and query building
- **Migrations**: Alembic for schema versioning and migrations
- **Migration Execution**: Run on application startup (with proper locking)
- **Models**: SQLAlchemy declarative models with Pydantic schema validation
- **Connection Management**: SQLAlchemy session pooling with async support

**Core Tables** (SQLAlchemy models with Pydantic schemas):

**FilingRecord** (Pydantic model):

- Tracks all fetched filings
- Links to storage location
- Includes checksum for integrity
- Timestamps for cache management

**AnalysisRecord** (Pydantic model):

- Analysis metadata and results reference
- LLM provider and model tracking
- Token usage and cost calculation
- Processing time metrics
- Status tracking through lifecycle

**TaskRecord** (Pydantic model):

- Task queue state management
- Worker assignment tracking
- Retry logic and error handling
- Priority-based processing

**UserAccountRecord** (Pydantic model):

- User tier and subscription status
- Rate limit counters (hourly/daily)
- Credit balance (for filing access + analyses)
- List of accessible filing IDs
- Concurrent task limits

**GlobalAnalysisRecord** (Pydantic model):

- `schema_version: int = 1`
- Analysis shared across all users
- Filing ID reference
- Analysis content storage key
- LLM model used (for quality tracking)
- Creation timestamp and cost
- Access count (for analytics)
- Quality score (for training dataset)
- **Future**: v2 with versioned analyses per model quality tier

**UsageTransactionRecord** (Pydantic model):

- Transaction type (filing access, analysis, bulk import)
- User ID and filing ID
- Amount charged
- Credit balance after transaction
- Timestamp and description

**Key Operations** (using Pydantic models for complex parameters):

- **Filing Management**:
  - `create_filing(filing: FilingRecord)` → `FilingId`
  - `get_filing(filing_id: FilingId)` → `Optional[FilingRecord]`
  - `filing_exists(request: FilingExistsRequest)` → `bool`
- **Analysis Tracking**:
  - `create_analysis(analysis: AnalysisRecord)` → `AnalysisId`
  - `update_analysis_status(request: StatusUpdateRequest)` → `bool`
  - `get_valid_analysis(request: ValidAnalysisRequest)` → `Optional[AnalysisRecord]`
- **Task Orchestration**:
  - `create_task(task: TaskRecord)` → `TaskId`
  - `claim_task(request: ClaimTaskRequest)` → `bool`
  - `update_task_status(request: TaskStatusRequest)` → `bool`

**Consistency Guarantees**:

- Unique constraints on filing identifiers (SQLAlchemy unique indexes)
- Atomic status updates (SQLAlchemy transactions)
- Optimistic locking for task claims (version columns)
- Migration lock for Alembic (prevent concurrent migrations)
- Session-level consistency with SQLAlchemy

## Rate Limiting & Usage Controls

### Pricing Model

**Global Analysis Pool**: All analyses are stored in a shared pool and can be accessed by any user who has paid for that filing.

### User Tiers & Pricing

**Demo Tier** (Free):

- **Rate Limits**: 10 requests/hour, 50 requests/day
- **Data Access**: Last 2 years only, S&P 500 companies only (pre-cached)
- **Filing Access**: Free for demo dataset
- **Analysis Credits**: $0.02 per filing analysis (pay-as-you-go)
- **Concurrent Analyses**: 1 at a time

**Basic Tier** ($X/month):

- **Rate Limits**: 100 requests/hour, 1000 requests/day
- **Data Access**: Last 5 years, Russell 1000 companies
- **Filing Access**: $0.10 per new filing fetched
- **Analysis Credits**: $0.02 per filing analysis
- **Bulk Import**: $5 per 100 filings
- **Concurrent Analyses**: 3 at a time
- **Monthly Credits**: $5 included for filings + analyses

**Professional Tier** ($XX/month):

- **Rate Limits**: 1000 requests/hour, 10000 requests/day
- **Data Access**: Last 10 years, all US public companies
- **Filing Access**: $0.05 per new filing fetched
- **Analysis Credits**: $0.015 per filing analysis
- **Bulk Import**: $20 per 1000 filings
- **Concurrent Analyses**: 10 at a time
- **Monthly Credits**: $25 included for filings + analyses

**Enterprise Tier** (Custom):

- **Rate Limits**: Custom/unlimited
- **Data Access**: Full historical data, global companies
- **Filing Access**: Custom pricing or unlimited
- **Analysis Credits**: Custom or BYOK (bring your own key)
- **Bulk Import**: Custom pricing
- **Concurrent Analyses**: Unlimited
- **API Access**: Direct API with custom integration

### Rate Limiting Implementation

**Per-User Rate Limiting** (Pydantic models):

```table
UserAccount:
- user_id: UserId
- tier: UserTier enum
- requests_per_hour: int
- requests_per_day: int
- credit_balance: float  # Combined filing + analysis credits
- credit_reset_date: datetime
- concurrent_tasks: int
- filings_accessed: List[FilingId]  # Track which filings user has paid for
```

**Rate Limit Enforcement Options**:

_Option 1 - Cloud Services (Production):_

1. **CloudFront/WAF**: Rate limiting by IP and geo-blocking
2. **API Gateway**: Built-in throttling per API key
3. **Database Level**: User quota tracking in Aurora
4. **Queue Level**: Priority queuing based on tier

_Option 2 - Application Level (Development/Fallback):_

1. **In-Memory Counters**: Simple rate limiting in Beanstalk instance
2. **Database Counters**: Rate limit tracking in Aurora
3. **Token Bucket Algorithm**: Implemented in application code
4. **Sliding Window**: Time-based request counting

### Usage-Based Billing

**Filing Access Pricing**:

- Check if filing exists in global pool
- If exists and user hasn't paid: charge filing access fee
- If doesn't exist: fetch from EDGAR and charge import fee
- Track which users have access to which filings

**Analysis Pricing**:

- Check if analysis exists for filing in global pool (at requested quality level)
- If exists: free access (someone already paid for it)
- If not: charge per-filing analysis fee based on tier and LLM choice
- Analysis becomes available to all users of that filing

**LLM Model Selection** (Future Feature):
_Initial Models (Ultra-Low Cost):_

- **GPT-5-nano**: OpenAI's upcoming efficient model ($0.01-0.02 per analysis)
- **gpt-oss-120b**: Open source uncensored model ($0.02-0.03 per analysis)
- **AWS Nova Lite**: Amazon's cost-optimized model ($0.01-0.02 per analysis)
- **Gemini-2.5-Flash-Lite**: Google's fast inference model ($0.01-0.02 per analysis)

_Future Optimization:_

- **Fine-tuned Custom Model**: Train small CPU-runnable model from golden dataset
- Collect high-quality input/output pairs from premium analyses
- Deploy on CPU instances for near-zero inference cost
- Fallback to cloud models for complex queries

**Billing Model** (Pydantic):

```table
UsageTransaction:
- user_id: UserId
- transaction_type: TransactionType enum (FILING_ACCESS, ANALYSIS, BULK_IMPORT)
- filing_id: Optional[FilingId]
- amount_usd: float
- credit_balance_after: float
- timestamp: datetime
```

### Data Access Controls

**Demo Data Prefilling**:

- Pre-fetch and cache 2 years of S&P 500 filings
- Store in separate "demo" storage bucket
- Serve from cache for instant response
- No EDGAR API calls for demo users

**Access Control Model** (Pydantic):

```table
DataAccessPolicy:
- tier: UserTier
- allowed_tickers: List[Ticker] | "ALL"
- max_years_history: int
- allowed_filing_types: List[FilingType]
- allowed_date_range: DateRange
```

### Usage Tracking & Metrics

**Metrics to Track** (for analytics, not limits):

- Total filings accessed per user
- Analysis requests per filing
- Storage used by global pool
- Cache hit rates for analyses
- Popular filings and companies
- User engagement patterns

**Abuse Prevention**:

- Exponential backoff for repeated failures
- Account suspension after N violations
- IP-based rate limiting for unauthenticated requests
- CAPTCHA for suspicious patterns

**System Limits** (platform-wide):

- Max execution time per analysis: 5 minutes
- Max filing size: 50MB
- Max tokens per LLM request: 100k
- Max concurrent workers: 100

**Monitoring & Alerts**:

- Alert on unusual usage patterns
- Daily/weekly usage reports
- Credit balance notifications (low balance alerts)
- System health and capacity monitoring

### Enforcement Points

1. **Frontend**: Display limits and current usage
2. **API Gateway**: First-line rate limiting
3. **Orchestrator**: Check quotas before queuing
4. **Worker**: Enforce execution limits
5. **Database**: Track and audit all usage
6. **Billing**: Monthly reconciliation and overages

## Task Workflow Architecture

### End-to-End Flow

**User Journey**:

1. User requests analysis via frontend
2. Frontend calls backend API with filing details
3. Backend validates user rate limits
4. Backend checks if user has tier access to requested data
5. Backend checks if filing exists in global pool
6. If filing doesn't exist: charge import fee and fetch from EDGAR
7. If filing exists but user hasn't accessed: charge access fee
8. Backend checks if analysis exists in global pool
9. If analysis exists: return immediately (free)
10. If not: check user has credits for new analysis
11. Queue task with tier-based priority
12. **Frontend establishes SSE connection for updates**
13. Worker picks up task and runs analysis
14. Worker stores analysis in global pool
15. Worker deducts analysis fee from user credits
16. **Worker publishes completion event**
17. **Backend pushes SSE update to frontend**
18. Frontend receives analysis via SSE (no polling)
19. User views analysis (now available to all users of that filing)

### System Layout

```graph
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│  API/Backend │◀─▶│   Database  │
│  (React/S3) │◀────│  (Beanstalk) │     │  (Aurora)   │
└─────────────┘ SSE └──────────────┘     └─────────────┘
                           │                     ▲
                           │                     │
                           ▼                     │
                    ┌─────────────┐              │
                    │   Storage   │              │
                    │     (S3)    │              │
                    └─────────────┘              │
                           ▲                     │
                           │                     │
                           ▼                     │
                    ┌─────────────┐              │
                    │ Queue (SQS) │              │
                    └─────────────┘              │
                           │                     │
                           ▼                     │
                    ┌─────────────┐              │
                    │   Workers   │──────────────┘
                    │  (Lambda)   │
                    └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
             ┌──────────┐  ┌──────────┐
             │  EDGAR   │  │   LLM    │
             │  Service │  │ Provider │
             └──────────┘  └──────────┘

Note: SSE connection from Backend to Frontend for real-time updates
```

### Queue Deduplication

- **Window**: Maximum allowed by provider
- **Key Pattern**: `{filing_id}_{user_email}`
- **Purpose**: Prevent duplicate processing for same user/filing
- **Implementation**: Native FIFO for SQS (5-min limit), cache/DB-based for RabbitMQ (configurable)

### Task Completion Notification

- **Primary**: Server-Sent Events (SSE) for real-time updates
- **Fallback**: Long polling for SSE-incompatible clients
- **Future**: WebSocket for bidirectional communication

## Component Responsibilities

### Elastic Beanstalk API Orchestrator

- **Role**: Central API service, always available
- **Responsibilities**:
  - Run Alembic migrations on startup (with distributed lock)
  - Handle all frontend HTTP requests
  - Validate requests and authenticate users
  - Enforce rate limits and usage quotas
  - Check database for existing valid analyses
  - Fetch completed analyses directly from storage
  - Queue new tasks to SQS (no direct processing)
  - **Manage SSE connections for real-time updates**
  - **Receive completion events from workers via SQS/SNS**
  - **Push updates to connected SSE clients**
  - Manage SQLAlchemy connection pool
  - Track user credits and enforce limits
- **Size**: t3.micro instance (2 vCPU, 1GB RAM)
- **Cost**: ~$7.50/month (with reserved instance or spot)

### Lambda Workers

- **Role**: Heavy processing workhorses
- **Responsibilities**:
  - Process SQS messages (analysis tasks)
  - Perform LLM API calls (AWS Bedrock Nova Lite or OpenRouter GPT-5-Nano)
  - Handle SEC API integration
  - Database writes (analysis results)
  - File processing and storage
- **Scaling**: Auto-scale 0 to hundreds based on queue depth
- **Cost**: ~$0.20-2.00/month for typical volumes

### SQS FIFO Queue

- **Role**: Task coordination and deduplication
- **Features**:
  - Message deduplication (prevents duplicate analyses)
  - FIFO ordering with tier-based priority
  - Dead letter queue for failed tasks
  - Visibility timeout for processing guarantees
  - Separate queues or message groups per tier
- **Deduplication Strategy**: Maximum provider window using filing_id + user_email
- **Priority Strategy**: Enterprise → Professional → Basic → Demo
- **Cost**: ~$0.50/month

### Aurora Serverless v2

- **Role**: Primary database
- **Features**:
  - True scale-to-zero (0 ACU minimum)
  - Auto-scaling based on demand
  - PostgreSQL compatibility
  - Automated backups to S3
- **Configuration**: 0 ACU minimum, 16 ACU maximum
- **Cost**: $0 when idle, ~$2-8/month when active

## Locking Strategy (Simplified)

### What We DON'T Need Locking For

- ✅ **Task deduplication**: Handled by SQS FIFO
- ✅ **Multiple analyses per filing**: Business logic allows this
- ✅ **Worker coordination**: SQS handles message distribution
- ✅ **Database race conditions**: Minimized with proper design

### Minimal Database Coordination

- **Approach**: Use database constraints + idempotent operations
- **Implementation**:
  - Unique constraints where needed
  - ON CONFLICT clauses for upserts
  - Atomic status updates
  - No distributed locks required

## Cost Breakdown (Monthly)

### Fixed Costs

```table
Elastic Beanstalk (t3.micro): $7.50
Elastic IP (for Beanstalk):   $3.60 (required for public access)
Route 53 Hosted Zone:         $0.50
Domain Name (.com):           $12/year = $1.00/month
CloudFront Distribution:      $0.00 (pay per request)
API Gateway (optional):       $3.50 (1M requests free tier)
Demo Data Storage (S3):       $2.00
Total Fixed:                  $18.10-21.60
```

### Variable Costs (Low Volume)

```table
Database (Aurora or CockroachDB): $0-8 (true scale-to-zero)
Lambda Executions:            $0.20-2.00
SQS Messages:                 $0.50
S3 Storage (global pool):     $5-10 (grows with content)
CloudFront Requests:          $0.50-1.00
Data Transfer:                $1-2
Total Variable:               $7.20-23.50
```

### **Total Platform Cost: $25-45/month**

### Required Network Infrastructure

```table
Domain & DNS:
- Domain registration:        $12/year via Route 53
- Route 53 Hosted Zone:       $0.50/month for DNS
- SSL Certificate:            Free via ACM

Public Access:
- Elastic IP for Beanstalk:   $3.60/month (required)
- Alternative: ALB            $16.20/month (when scaling)

Rate Limiting Options:
- CloudFront + AWS WAF:       IP-based rate limiting
- API Gateway:                Built-in throttling
- Application level:          Zero additional cost
```

### **LLM Provider Strategy**

**Phase 1 - Launch (Cloud Models)**:

- **Primary**: AWS Nova Lite - $0.06/1M input, $0.015/1M output tokens
- **Backup**: Gemini-2.5-Flash-Lite - Similar ultra-low pricing
- **Premium**: GPT-5-nano (when available) - Expected ~$0.10/1M tokens
- **Open Source**: gpt-oss-120b - Self-hosted on Lambda for uncensored analysis

**Phase 2 - Optimization (Custom Model)**:

- Collect golden dataset from user-validated analyses
- Fine-tune small model (7B-13B parameters)
- Deploy on CPU instances (t4g.medium)
- Reduce inference cost to ~$0.001 per analysis
- Keep cloud models for complex/edge cases

### **Cost Savings vs Traditional Setup**

- **No ALB**: Saves $16.20/month (-73% reduction)
- **True scale-to-zero DB**: Saves $5-10/month when idle
- **Serverless workers**: Only pay for actual usage

## Scaling Strategy

### Phase 1: Launch (0-1K users)

- Single Beanstalk instance
- Aurora at minimum ACU
- Lambda workers auto-scale as needed
- Basic monitoring with CloudWatch

### Phase 2: Growth (1K-10K users)

- **Add Application Load Balancer** (enable auto-scaling)
- Upgrade Beanstalk to t3.small instance
- Aurora auto-scaling up to 4 ACU
- Add CloudWatch alarms
- Implement basic caching

### Phase 3: Scale (10K+ users)

- Multi-AZ deployment
- Multiple Beanstalk instances with auto-scaling
- Read replicas for database
- CDN optimization

## Implementation Architecture

### Service Layer Structure

The codebase follows a clean architecture pattern with clear separation:

**Application Layer** (`/application`):

- **Interfaces**: Protocol definitions for all external services
- **Services**: Business logic orchestration and task management
- **Factory**: Dependency injection and service registration

**Infrastructure Layer** (`/infrastructure`):

- **Storage**: S3 and local filesystem implementations
- **Queue**: SQS and RabbitMQ message queue implementations
- **Worker**: Lambda and Docker worker implementations
- **Data Sources**: EDGAR and future data provider integrations
- **LLM**: OpenAI, Bedrock, and other LLM provider implementations
- **Database**:
  - SQLAlchemy models and repositories
  - Alembic migrations directory
  - Database connection management
  - Query builders and utilities

**Shared Layer** (`/shared`):

- **Config**: Environment-based settings with Pydantic BaseSettings
- **Models**: Pydantic models for all data structures
- **Types**: Common type definitions (UUID types, enums)
- **Utils**: Shared utilities and helpers

### Configuration Management

**Configuration Provider Interface**:

System will support multiple configuration sources through a provider interface:

- **JSONConfigProvider**: Local JSON files for development
- **AWSParameterStoreProvider**: AWS Systems Manager for production configs
- **EnvironmentConfigProvider**: Environment variables as override
- **CompositeConfigProvider**: Merge multiple sources with precedence

**Secret Manager Interface**:

Separate interface for managing sensitive values:

```table
ISecretManager (Protocol):
- get_secret(key: str) → SecretStr
- get_secrets(keys: List[str]) → Dict[str, SecretStr]
- set_secret(key: str, value: str) → bool
- delete_secret(key: str) → bool
- list_secrets() → List[str]
- rotate_secret(key: str) → SecretStr

Implementations:
- AWSSecretsManager: AWS Secrets Manager with rotation support
- EnvFileSecretManager: .env files for local development
- InMemorySecretManager: Testing and development
- VaultSecretManager: HashiCorp Vault (future)
```

**Secret Categories**:

- **API Keys**: OpenAI, Anthropic, third-party services
- **Database Credentials**: Password, connection strings
- **JWT Secrets**: Token signing keys
- **Encryption Keys**: Data encryption at rest
- **OAuth Credentials**: Client secrets for SSO

**Provider-Specific Configuration Models**:

Each external service will have its own versioned configuration model:

**LLM Providers** (all include `config_version: int = 1`):

- **OpenAIConfig**: API key (from SecretManager), model ID, organization ID, custom endpoints
- **BedrockConfig**: Model ID, AWS region, runtime endpoint (uses IAM role)
- **GeminiConfig**: API key (from SecretManager), model ID, project ID
- **OSSModelConfig**: Model ID, endpoint URL, optional auth (from SecretManager)
- **Future**: v2 for new authentication methods, v3 for new model parameters

**Storage Providers** (all include `config_version: int = 1`):

- **S3Config**: Bucket name, region, prefix, endpoint URL
- **LocalStorageConfig**: Base path, max size
- **Future**: v2 for new storage APIs, v3 for encryption options

**Queue Providers** (all include `config_version: int = 1`):

- **SQSConfig**: Queue URL, region, message group ID
- **RabbitMQConfig**: Connection URL, exchange, routing key
- **Future**: v2 for new message formats, v3 for routing strategies

**Database Providers** (all include `config_version: int = 1`):

- **AuroraConfig**: Connection endpoint, credentials (from SecretManager)
- **PostgresConfig**: Connection string (password from SecretManager), pool size
- **Future**: v2 for connection pooling strategies

**Main Settings Structure**:

All configurable parameters centralized in Settings model:

**Provider Selection**:

- Single enum per service type (storage, queue, worker, database, LLM)
- Provider configs injected based on selection
- Fallback providers with priority ordering

**Business Logic Parameters** (all configurable):

- Cache validity window (hours)
- Deduplication window (seconds)
- Rate limits per tier
- Pricing per tier and operation
- Concurrent task limits
- Bulk import settings

**Timeouts & Retries**:

- Task execution timeout
- Retry count and backoff
- Health check intervals
- Connection timeouts
- Queue visibility timeout

**LLM Common Parameters**:

- Temperature, max tokens, top_p
- Frequency and presence penalties
- Request timeout
- Model quality tiers

**Demo Mode Settings**:

- Allowed tickers list
- Years of history
- Daily/hourly limits
- Storage prefix

**Feature Flags**:

- LLM model selection
- Bulk import
- Custom model usage
- SSE real-time updates (enabled by default)
- WebSocket updates (future)
- Rate limiting
- Demo mode
- Long polling fallback

**Resource Limits** (Defined in IaC using Pulumi):

Infrastructure limits will be defined in Pulumi configuration:

- **Compute**: CPU and memory for Beanstalk/Lambda
- **Database**: Min/max ACUs for Aurora
- **Queue**: Message retention, visibility timeout
- **Storage**: Lifecycle policies, versioning
- **Network**: Rate limits, request/response sizes

**Configuration Loading Strategy**:

1. Initialize SecretManager based on environment
2. Load base configuration from primary source
3. Fetch secrets from SecretManager
4. Override with environment-specific settings
5. Apply environment variables as final override
6. Validate all required fields present
7. Type coercion and validation via Pydantic
8. Cache configuration with optional hot-reload

**Secret Rotation Strategy**:

- Automatic rotation for database passwords (30 days)
- API key rotation with grace period (60 days)
- JWT secret rotation with dual-key support
- Notification before expiration
- Zero-downtime rotation process

### Dependency Injection Pattern

**Service Registry Architecture**:

The system uses a registry pattern for clean dependency injection:

1. **Service Registration**:

   - Each provider implementation registers with its interface
   - Registration happens at startup
   - Allows runtime provider selection

2. **Factory Pattern**:

   - `ApplicationFactory` creates services based on configuration
   - Each service gets appropriate configuration
   - Type-safe service creation with Protocol checking

3. **Orchestrator Creation**:
   - Central orchestrator receives required services:
     - Storage (for fetching completed analyses)
     - Queue (for task submission)
     - Database (for metadata queries)
     - SecretManager (for credential access)
   - No direct dependencies between services
   - Workers receive their own service dependencies
   - Easy testing with mock implementations

**Benefits**:

- Provider-agnostic business logic
- Easy testing with mock services
- Clean separation of concerns
- Runtime provider switching
- Type safety throughout

**Service Lifecycle**:

1. Initialize SecretManager based on environment
2. Load configuration from environment
3. Fetch secrets from SecretManager
4. Register all service implementations
5. Factory creates service instances with secrets
6. Inject services into orchestrator
7. Application ready to process requests

## Deployment Strategy

### GitHub Actions Workflows

1. **CI Pipeline**: Testing, linting, security scanning
2. **Database Migration**: Run Alembic migrations before deployment
3. **Beanstalk Deployment**: Build + deploy API application
4. **Lambda Deployment**: Package + deploy worker functions
5. **Frontend Deployment**: Build React + deploy to S3/CloudFront

### Infrastructure as Code

- **Beanstalk Configuration**: YAML configs for Beanstalk
- **Lambda Functions**: Automated packaging from src/
- **AWS Resources**: CloudFormation or CDK (future)

### Environment Management

- **Production**: main branch auto-deploy
- **Staging**: feature branch testing (optional)
- **Local Development**: Docker Compose for parity

## Key Benefits of This Architecture

### Simplicity

- ✅ Minimal components to manage
- ✅ Clear separation of concerns
- ✅ Standard AWS services (no exotic tools)
- ✅ Familiar development patterns

### Cost Effectiveness

- ✅ Pay-per-use for workers (Lambda)
- ✅ Scale-to-zero database
- ✅ Efficient resource utilization
- ✅ No over-provisioning

### Reliability

- ✅ Managed services (less operational overhead)
- ✅ Auto-scaling and self-healing
- ✅ Built-in redundancy where needed
- ✅ Graceful degradation

### Developer Experience

- ✅ Local development matches production
- ✅ Easy debugging and monitoring
- ✅ Familiar tech stack (FastAPI, React, PostgreSQL)
- ✅ Simple deployment process

## Security Considerations

### Network Security

- VPC with private subnets for database
- Security groups with minimal access
- HTTPS everywhere with free SSL certificates
- **Future**: ALB with WAF protection when scaling

### Access Control

- IAM roles with least privilege
- Secrets Manager for API keys
- No hardcoded credentials
- Environment-specific configurations

### Data Protection

- Encryption at rest (Aurora, S3)
- Encryption in transit (TLS)
- Regular backups to S3
- Audit logging enabled

## Monitoring and Observability

### Logging Provider Interface

**Generic Logging Abstraction**:

- Structured logging with levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Context enrichment with trace IDs, user IDs, request IDs
- Batch logging for performance
- Query interface for log retrieval
- Automatic flushing and rotation

**CloudWatch Implementation (AWS)**:

- Separate log groups for each service component
- JSON structured logging for CloudWatch Insights queries
- Retention policies: 7 days (demo), 30 days (standard), 90 days (enterprise)
- Metric filters for automatic alerting on error patterns
- Cost optimization through sampling and compression

**Local Implementation (Development)**:

- Rotating file logs with configurable size/time limits
- Optional syslog integration for centralized logging
- stdout/stderr for container environments
- Environment-based log level filtering
- Human-readable formatting for development

**Log Event Structure**:

- Timestamp (ISO 8601)
- Log level (enum)
- Message (string)
- Context (key-value pairs)
- Correlation IDs (trace, span, user, request)
- Service metadata (version, environment, instance)

### Basic Monitoring (Launch)

- CloudWatch metrics for all services
- ECS health checks (automatic restart)
- Lambda error tracking
- Database performance insights
- Structured logging with correlation IDs

### Enhanced Monitoring (Growth)

- Custom application metrics
- Distributed tracing (X-Ray/OpenTelemetry)
- Log aggregation and analysis
- Performance alerts
- Cost anomaly detection

## Next Steps

1. **Create Service Interfaces**: Define abstract interfaces for all external services
2. **Implement Storage Services**: Build S3 and local storage implementations
3. **Implement Queue Services**: Build SQS and RabbitMQ implementations
4. **Update Worker Logic**: Refactor to use new service interfaces
5. **Infrastructure Setup**: Create AWS resources with Terraform/CloudFormation
6. **CI/CD Implementation**: GitHub Actions workflows for multi-environment deployment
7. **Integration Testing**: Test both local and AWS configurations
8. **Performance Testing**: Validate queue deduplication and worker scaling
9. **Launch**: Production deployment with monitoring

## Risk Mitigation

### Technical Risks

- **Aurora cold starts**: Minimal impact with connection pooling
- **Lambda cold starts**: Acceptable for background processing
- **SQS message failures**: Dead letter queue for retry logic
- **Network issues**: ALB health checks and auto-recovery

### Cost Risks

- **Unexpected scaling**: CloudWatch billing alerts
- **Resource over-provisioning**: Regular cost reviews
- **Data transfer costs**: Keep everything in same region

### Operational Risks

- **Single point of failure**: Multi-AZ for critical components
- **Deployment failures**: Blue-green deployment strategy
- **Security vulnerabilities**: Regular security scanning
- **Data loss**: Automated backups and point-in-time recovery
