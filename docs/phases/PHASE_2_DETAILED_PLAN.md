# Phase 2: Core Domain Implementation - Detailed Plan

## Overview
**Duration**: Week 3 (5 days)  
**Goal**: Implement the core domain layer with SEC filing business logic  
**Status**: Ready to begin implementation

## Git Branch Strategy

### Branch Structure
```
main
└── feature/phase-2-domain-layer (main feature branch)
    ├── feature/domain-value-objects (Day 1)
    ├── feature/domain-entities (Day 2-3)
    ├── feature/domain-repositories (Day 4)
    └── feature/domain-services (Day 5)
```

### Branch Commands
```bash
# Create main feature branch
git checkout -b feature/phase-2-domain-layer

# Create sub-branches as needed
git checkout -b feature/domain-value-objects
git checkout -b feature/domain-entities
git checkout -b feature/domain-repositories  
git checkout -b feature/domain-services
```

## Task Breakdown

### **Day 1: Value Objects Foundation** - ✅ COMPLETED & SIMPLIFIED
**Branch**: `feature/domain-value-objects` - **MERGED AND REFACTORED**

#### 1.1 SEC Identifiers - ✅ COMPLETED & SIMPLIFIED
- [x] **Create `src/domain/value_objects/cik.py`** - ✅ SIMPLIFIED
  - CIK validation with 10-digit format
  - Proper string representation and equality
  - ~~Zero-padded formatting method~~ (removed - use edgartools)
  - Comprehensive unit tests (simplified)

- [x] **Create `src/domain/value_objects/ticker.py`** - ✅ KEPT UNCHANGED
  - Ticker validation (1-5 uppercase letters)
  - Normalization to uppercase
  - String representation and equality
  - Comprehensive unit tests

- [x] **Create `src/domain/value_objects/accession_number.py`** - ✅ SIMPLIFIED
  - SEC accession number format validation
  - ~~CIK, year, and sequence extraction methods~~ (removed - use edgartools)
  - Comprehensive unit tests (simplified)

#### 1.2 Filing Types and Dates - ✅ COMPLETED & SIMPLIFIED
- [x] **Create `src/domain/value_objects/filing_type.py`** - ✅ SIMPLIFIED
  - FilingType enumeration with all major forms
  - ~~Periodic, annual, and quarterly classification methods~~ (removed - use edgartools)
  - Only kept `is_amendment()` method
  - Comprehensive unit tests (simplified)

- [x] **~~Create `src/domain/value_objects/filing_date.py`~~** - ✅ REMOVED
  - ~~Filing date validation and representation~~ (removed - use edgartools)
  - ~~Fiscal year and quarter calculation~~ (removed - use edgartools)
  - ~~Business day validation~~ (removed - use edgartools)

#### 1.3 Financial Data Types - ✅ COMPLETED & SIMPLIFIED
- [x] **Create `src/domain/value_objects/money.py`** - ✅ KEPT UNCHANGED
  - Money object with currency support
  - Arithmetic operations (+, -, *)
  - Decimal precision handling
  - Comprehensive unit tests (essential for analysis)

- [x] **~~Create `src/domain/value_objects/financial_period.py`~~** - ✅ REMOVED
  - ~~Financial period with start/end dates~~ (removed - use edgartools XBRL)
  - ~~Annual/quarterly classification~~ (removed - use edgartools)
  - ~~Duration calculation methods~~ (removed - use edgartools)

#### 1.4 Processing Status - ✅ COMPLETED & KEPT
- [x] **Create `src/domain/value_objects/processing_status.py`** - ✅ KEPT UNCHANGED
  - ProcessingStatus enumeration
  - State transition validation logic
  - Comprehensive unit tests (essential for analysis pipeline)

**Day 1 Summary**: 6 value objects (simplified from 8) with focus on analysis, 171 unit tests passing, full type safety.

### **Day 2-3: Core Entities** - ✅ COMPLETED
**Branch**: `feature/domain-entities` - **READY TO MERGE**

**Status**: Entities simplified for analysis focus, removing edgartools duplicates

**Git Commands**:
```bash
# Working on domain-entities branch
git checkout feature/domain-entities
# Ready to merge to domain-layer branch
```

#### 2.1 Company Entity (Day 2) - ✅ COMPLETED
- [x] **Create `src/domain/entities/company.py`** - ✅ SIMPLIFIED
  ```python
  class Company:
      """Minimal company entity for reference purposes"""
      def __init__(self, 
                   id: UUID,
                   cik: CIK,
                   name: str,
                   metadata: Dict[str, Any] = None)
      
      # Key simplifications:
      # - Removed ticker, sic_code, is_active (use edgartools)
      # - Removed business methods (use edgartools)
      # - Focus on essential reference data only
      # - 14 comprehensive unit tests
  ```

#### 2.2 Filing Entity (Day 2) - ✅ COMPLETED
- [x] **Create `src/domain/entities/filing.py`** - ✅ SIMPLIFIED
  ```python
  class Filing:
      """SEC filing entity focused on processing status"""
      def __init__(self,
                   id: UUID,
                   company_id: UUID,
                   accession_number: AccessionNumber,
                   filing_type: FilingType,
                   filing_date: date,
                   processing_status: ProcessingStatus = ProcessingStatus.PENDING,
                   processing_error: Optional[str] = None,
                   metadata: Dict[str, Any] = None)
      
      # Key simplifications:
      # - Removed period_end_date, file_urls (use edgartools)
      # - Removed business classification methods (use edgartools)
      # - Focus on processing status tracking only
      # - 20 comprehensive unit tests
  ```

#### 2.3 Financial Statement Entities (Day 3) - ✅ REMOVED
- [x] **~~Create `src/domain/entities/financial_statement.py`~~** - ✅ REMOVED
  ```python
  # REMOVED: EdgarTools provides comprehensive financial statement parsing
  # via company.financials.balance_sheet(), .income_statement(), etc.
  # No need to duplicate this functionality
  ```

- [x] **~~Create `src/domain/entities/financial_line_item.py`~~** - ✅ REMOVED
  ```python
  # REMOVED: EdgarTools provides rich financial line item data
  # Classification methods are better handled by edgartools
  ```

#### 2.4 XBRL Fact Entity (Day 3) - ✅ REMOVED
- [x] **~~Create `src/domain/entities/xbrl_fact.py`~~** - ✅ REMOVED
  ```python
  # REMOVED: EdgarTools has superior XBRL parsing via XBRL.from_filing()
  # and XBRLS.from_filings() - no need to duplicate
  ```

#### 2.5 Analysis Entity (Day 3) - ✅ COMPLETED
- [x] **Create `src/domain/entities/analysis.py`** - ✅ FULL IMPLEMENTATION
  ```python
  class AnalysisType(str, Enum):
      FINANCIAL_SUMMARY = "financial_summary"
      RISK_ANALYSIS = "risk_analysis"
      RATIO_ANALYSIS = "ratio_analysis"
      TREND_ANALYSIS = "trend_analysis"
      PEER_COMPARISON = "peer_comparison"
      SENTIMENT_ANALYSIS = "sentiment_analysis"
      KEY_METRICS = "key_metrics"
      ANOMALY_DETECTION = "anomaly_detection"
      CUSTOM = "custom"
      
  class Analysis:
      """Analysis result entity - CORE to analysis system"""
      def __init__(self,
                   id: UUID,
                   filing_id: UUID,
                   analysis_type: AnalysisType,
                   created_by: UUID,
                   results: Dict[str, Any] = None,
                   llm_provider: Optional[str] = None,
                   llm_model: Optional[str] = None,
                   confidence_score: Optional[float] = None,
                   metadata: Dict[str, Any] = None,
                   created_at: Optional[datetime] = None)
      
      # Rich analysis methods (27 comprehensive unit tests)
      def is_high_confidence(self) -> bool
      def get_summary(self) -> str
      def get_key_findings(self) -> List[str]
      def get_risks(self) -> List[Dict[str, Any]]
      def get_opportunities(self) -> List[Dict[str, Any]]
      def get_metrics(self) -> Dict[str, Any]
      def add_insight(self, key: str, value: Any) -> None
      def add_metric(self, name: str, value: Any, unit: str = None) -> None
      def add_risk(self, description: str, severity: str, ...) -> None
      def update_confidence_score(self, score: float) -> None
      def is_llm_generated(self) -> bool
  ```

### **Day 4: Repository Interfaces** - REVISED FOR ANALYSIS FOCUS
**Branch**: `feature/domain-repositories`

#### 4.1 Base Repository
- [ ] **Create `src/domain/repositories/base.py`**
  ```python
  class BaseRepository(ABC):
      """Abstract base repository for analysis-focused entities"""
      
      @abstractmethod
      async def save(self, entity: Any) -> None
      
      @abstractmethod
      async def find_by_id(self, id: UUID) -> Optional[Any]
      
      @abstractmethod
      async def delete(self, id: UUID) -> None
      
      @abstractmethod
      async def find_all(self, 
                        limit: int = 100, 
                        offset: int = 0) -> List[Any]
  ```

#### 4.2 Company Repository
- [ ] **Create `src/domain/repositories/company_repository.py`**
  ```python
  class CompanyRepository(BaseRepository):
      """Company data access interface"""
      
      @abstractmethod
      async def find_by_cik(self, cik: CIK) -> Optional[Company]
      
      @abstractmethod
      async def find_by_ticker(self, ticker: Ticker) -> Optional[Company]
      
      @abstractmethod
      async def search(self, query: str) -> List[Company]
      
      @abstractmethod
      async def find_active_companies(self) -> List[Company]
  ```

#### 4.3 Filing Repository
- [ ] **Create `src/domain/repositories/filing_repository.py`**
  ```python
  class FilingFilters:
      """Filing search filters"""
      def __init__(self,
                   filing_types: Optional[List[FilingType]] = None,
                   date_from: Optional[date] = None,
                   date_to: Optional[date] = None,
                   status: Optional[ProcessingStatus] = None)
                   
  class FilingRepository(BaseRepository):
      """Filing data access interface"""
      
      @abstractmethod
      async def find_by_accession(self, 
                                 accession: AccessionNumber) -> Optional[Filing]
      
      @abstractmethod
      async def find_by_company(self, 
                               company_id: UUID, 
                               filters: FilingFilters) -> List[Filing]
      
      @abstractmethod
      async def get_latest_by_type(self, 
                                  company_id: UUID, 
                                  filing_type: FilingType) -> Optional[Filing]
      
      @abstractmethod
      async def find_unprocessed(self, limit: int = 100) -> List[Filing]
  ```

#### 4.4 ~~Financial Data Repository~~ - REMOVED
- [x] **~~Create `src/domain/repositories/financial_data_repository.py`~~** - REMOVED
  ```python
  # REMOVED: We use edgartools directly for all financial data access
  # No need for a financial data repository as we don't store SEC data
  # Focus on AnalysisRepository for storing analysis results
  ```

#### 4.4 Analysis Repository - PRIMARY FOCUS
- [ ] **Create `src/domain/repositories/analysis_repository.py`**
  ```python
  class AnalysisRepository(BaseRepository):
      """Analysis results storage - CORE repository for our value proposition"""
      
      @abstractmethod
      async def find_by_filing(self, filing_id: UUID) -> List[Analysis]
      
      @abstractmethod
      async def find_by_type(self, 
                            analysis_type: AnalysisType) -> List[Analysis]
      
      @abstractmethod
      async def find_by_user(self, user_id: UUID) -> List[Analysis]
      
      @abstractmethod
      async def find_by_company(self, 
                               company_id: UUID,
                               analysis_type: Optional[AnalysisType] = None) -> List[Analysis]
      
      @abstractmethod
      async def find_recent(self, 
                           limit: int = 10,
                           analysis_type: Optional[AnalysisType] = None) -> List[Analysis]
      
      @abstractmethod
      async def find_high_confidence(self, 
                                    threshold: float = 0.8) -> List[Analysis]
  ```

### **Day 5: Domain Services & Events** - REVISED FOR ANALYSIS FOCUS
**Branch**: `feature/domain-services`

#### 5.1 Domain Services
- [ ] **Create `src/domain/services/analysis_orchestrator.py`**
  ```python
  class AnalysisOrchestrator:
      """Orchestrates multi-step analysis processes"""
      
      def __init__(self, 
                   analysis_repo: AnalysisRepository,
                   filing_repo: FilingRepository)
      
      async def orchestrate_filing_analysis(self, 
                                          filing_id: UUID,
                                          analysis_types: List[AnalysisType]) -> List[Analysis]
      async def aggregate_insights(self, analyses: List[Analysis]) -> Dict[str, Any]
      async def detect_anomalies(self, 
                                company_id: UUID,
                                current_analysis: Analysis) -> List[Dict[str, Any]]
      async def generate_executive_summary(self, analyses: List[Analysis]) -> str
  ```

- [ ] **Create `src/domain/services/insight_generator.py`**
  ```python
  class InsightGenerator:
      """Derives actionable insights from analysis results"""
      
      def __init__(self, analysis_repo: AnalysisRepository)
      
      async def extract_key_insights(self, analysis: Analysis) -> List[str]
      async def identify_trends(self, 
                               company_id: UUID,
                               time_period: int = 12) -> Dict[str, Any]
      async def compare_peer_performance(self, 
                                       analysis: Analysis,
                                       peer_analyses: List[Analysis]) -> Dict[str, Any]
      async def generate_recommendations(self, 
                                       insights: List[Dict[str, Any]]) -> List[str]
  ```

- [ ] **~~Create `src/domain/services/financial_calculator.py`~~** - REMOVED
  ```python
  # REMOVED: Use edgartools FinancialRatios class instead
  # from edgar.xbrl.analysis.ratios import FinancialRatios
  # No need to duplicate financial calculation logic
  ```

#### 5.2 Domain Events
- [ ] **Create `src/domain/events/base.py`**
  ```python
  class DomainEvent:
      """Base domain event"""
      def __init__(self, 
                   event_id: UUID,
                   occurred_at: datetime,
                   event_type: str,
                   aggregate_id: UUID)
  ```

- [ ] **Create `src/domain/events/filing_events.py`**
  ```python
  class FilingCreatedEvent(DomainEvent):
      def __init__(self, filing: Filing)
      
  class FilingProcessedEvent(DomainEvent):
      def __init__(self, filing: Filing)
      
  class AnalysisCompletedEvent(DomainEvent):
      def __init__(self, analysis: Analysis)
  ```

#### 5.3 Domain Exceptions
- [ ] **Create `src/domain/exceptions/base.py`**
  ```python
  class DomainException(Exception):
      """Base domain exception"""
      pass
  ```

- [ ] **Create `src/domain/exceptions/validation.py`**
  ```python
  class ValidationException(DomainException):
      pass
      
  class InvalidCIKException(ValidationException):
      pass
      
  class InvalidTickerException(ValidationException):
      pass
      
  class InvalidFilingTypeException(ValidationException):
      pass
  ```

- [ ] **Create `src/domain/exceptions/business.py`**
  ```python
  class BusinessException(DomainException):
      pass
      
  class FilingNotFoundException(BusinessException):
      pass
      
  class DuplicateFilingException(BusinessException):
      pass
      
  class ProcessingException(BusinessException):
      pass
  ```

## Testing Strategy

### Unit Tests Structure
```
tests/unit/domain/
├── test_value_objects/
│   ├── test_cik.py
│   ├── test_ticker.py
│   ├── test_accession_number.py
│   ├── test_filing_type.py
│   ├── test_filing_date.py
│   ├── test_money.py
│   └── test_financial_period.py
├── test_entities/
│   ├── test_company.py
│   ├── test_filing.py
│   ├── test_financial_statement.py
│   ├── test_xbrl_fact.py
│   └── test_analysis.py
└── test_services/
    ├── test_filing_processor.py
    └── test_financial_calculator.py
```

### Test Coverage Requirements
- [ ] **Value Objects**: 100% coverage
- [ ] **Entities**: 95% coverage  
- [ ] **Services**: 90% coverage
- [ ] **All tests must pass mypy strict mode**

### Test Commands
```bash
# Run domain tests
poetry run pytest tests/unit/domain/ -v

# Run with coverage
poetry run pytest tests/unit/domain/ --cov=src/domain --cov-report=html

# Type check
poetry run mypy src/domain/

# Format code
poetry run black src/domain/ tests/unit/domain/
poetry run isort src/domain/ tests/unit/domain/
```

## Definition of Done

### Value Objects (Day 1) - ✅ COMPLETED
- [x] All value objects implement proper validation
- [x] Immutable by design
- [x] Equality comparison implemented
- [x] String representation methods
- [x] 100% test coverage
- [x] All tests pass mypy strict mode
- [x] Code follows clean architecture principles

### Entities (Day 2-3) - ✅ COMPLETED
- [x] Business logic encapsulated in entities (simplified for analysis focus)
- [x] No infrastructure dependencies
- [x] Proper state management
- [x] Domain invariants enforced
- [x] Rich business methods (Analysis entity) with minimal reference entities (Company, Filing)

### Repository Interfaces (Day 4) - REVISED
- [ ] Abstract base classes defined (focused on analysis storage)
- [ ] Database-agnostic interfaces
- [ ] Async/await support
- [ ] Proper method signatures
- [ ] Documentation strings
- [ ] FinancialDataRepository removed (use edgartools directly)

### Domain Services (Day 5) - REVISED
- [ ] Analysis orchestration services implemented
- [ ] Insight generation logic defined
- [ ] Repository dependencies injected (analysis-focused)
- [ ] Domain events published for analysis milestones
- [ ] Exception handling for analysis failures
- [ ] Unit tests written
- [ ] FinancialCalculator removed (use edgartools)

### Overall Phase 2 Success Criteria
- [x] **Value Objects**: Domain layer foundation complete (✅)
- [ ] **Entities**: Business logic encapsulated in domain entities
- [ ] **Repositories**: Database-agnostic interfaces defined
- [ ] **Services**: Domain business logic services implemented
- [ ] Domain layer is completely independent of infrastructure
- [ ] All business rules are enforced in domain layer
- [ ] Code passes mypy strict mode
- [ ] 95%+ test coverage
- [ ] No circular dependencies
- [ ] All public methods have docstrings
- [ ] Code follows DDD principles
- [ ] Ready for Phase 3 infrastructure implementation

### Current Status Summary
- **Phase 2 Progress**: 60% complete (Day 1-3 of 5 days)
- **Value Objects**: 6/6 implemented (simplified) with full test coverage
- **Entities**: 3/3 implemented (simplified for analysis focus) with full test coverage
- **Test Coverage**: 171 unit tests passing, mypy strict mode passing
- **Next Step**: Begin Day 4 repository interfaces (optional for analysis focus)
- **Branch Status**: `feature/domain-entities` ready to merge to `feature/domain-layer`

## Refactoring Summary: Analysis-Focused Domain Layer

### Key Simplification Decisions
The domain layer was refactored to focus on **analysis** rather than duplicating edgartools functionality:

#### **What We Kept (Core Analysis Focus)**
- **Analysis Entity**: Full implementation - this is our core differentiator for storing LLM insights, custom metrics, and analysis results
- **Money**: Essential for financial calculations and precision in analysis
- **ProcessingStatus**: Critical for analysis pipeline workflow management
- **Ticker**: Simple validation, already minimal
- **Company**: Minimal reference entity (id, cik, name) for analysis context
- **Filing**: Focused on processing status tracking for analysis pipeline

#### **What We Simplified**
- **AccessionNumber**: Removed `get_cik()`, `get_year()`, `get_sequence()` - use edgartools parsing
- **CIK**: Removed `to_padded_string()` - use edgartools formatting
- **FilingType**: Removed classification methods - use edgartools, kept only `is_amendment()`

#### **What We Removed**
- **FilingDate**: Removed entirely - edgartools provides fiscal year/quarter logic
- **FinancialPeriod**: Removed entirely - edgartools provides XBRL period data
- **FinancialStatement**: Removed entirely - edgartools provides `company.financials.balance_sheet()` etc.
- **FinancialLineItem**: Removed entirely - edgartools provides rich financial line item data
- **XBRLFact**: Removed entirely - edgartools has superior XBRL parsing

### Benefits of This Approach
1. **~80% reduction** in domain code complexity
2. **No duplication** of edgartools functionality  
3. **Clear separation** of concerns - edgartools for SEC data, Aperilex for analysis
4. **Focused codebase** - every line serves the analysis mission
5. **Better maintainability** - fewer moving parts, cleaner architecture
6. **Leverages expertise** - edgartools handles SEC compliance, we handle analysis

## EdgarTools Integration Notes

Reference Context7 Library ID: `/dgunning/edgartools` for:
- All SEC data retrieval and parsing
- Company and Filing detailed information
- XBRL fact structure and financial statements
- Business rule validation and SEC compliance
- Financial data formatting and calculations

**Aperilex Role**: Focus on analysis orchestration, results storage, and insight generation while leveraging edgartools for all SEC data access.