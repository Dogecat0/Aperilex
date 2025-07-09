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

### **Day 1: Value Objects Foundation** - ✅ COMPLETED
**Branch**: `feature/domain-value-objects` - **MERGED**

#### 1.1 SEC Identifiers - ✅ COMPLETED
- [x] **Create `src/domain/value_objects/cik.py`** - ✅ DONE
  - CIK validation with 10-digit format
  - Proper string representation and equality
  - Zero-padded formatting method
  - Comprehensive unit tests

- [x] **Create `src/domain/value_objects/ticker.py`** - ✅ DONE
  - Ticker validation (1-5 uppercase letters)
  - Normalization to uppercase
  - String representation and equality
  - Comprehensive unit tests

- [x] **Create `src/domain/value_objects/accession_number.py`** - ✅ DONE
  - SEC accession number format validation
  - CIK, year, and sequence extraction methods
  - Comprehensive unit tests

#### 1.2 Filing Types and Dates - ✅ COMPLETED
- [x] **Create `src/domain/value_objects/filing_type.py`** - ✅ DONE
  - FilingType enumeration with all major forms
  - Periodic, annual, and quarterly classification methods
  - Comprehensive unit tests

- [x] **Create `src/domain/value_objects/filing_date.py`** - ✅ DONE
  - Filing date validation and representation
  - Fiscal year and quarter calculation
  - Business day validation
  - Comprehensive unit tests

#### 1.3 Financial Data Types - ✅ COMPLETED
- [x] **Create `src/domain/value_objects/money.py`** - ✅ DONE
  - Money object with currency support
  - Arithmetic operations (+, -, *)
  - Decimal precision handling
  - Comprehensive unit tests

- [x] **Create `src/domain/value_objects/financial_period.py`** - ✅ DONE
  - Financial period with start/end dates
  - Annual/quarterly classification
  - Duration calculation methods
  - Comprehensive unit tests

#### 1.4 Processing Status - ✅ COMPLETED
- [x] **Create `src/domain/value_objects/processing_status.py`** - ✅ DONE
  - ProcessingStatus enumeration
  - State transition validation logic
  - Comprehensive unit tests

**Day 1 Summary**: All 8 value objects implemented with 100% test coverage, passing mypy strict mode.

### **Day 2-3: Core Entities** - 🔄 READY TO START
**Branch**: `feature/domain-entities` - **TO BE CREATED**

**Prerequisites**: Value objects branch merged into `feature/phase-2-domain-layer`

**Git Commands**:
```bash
# Ensure you're on the main feature branch with value objects merged
git checkout feature/phase-2-domain-layer
git merge feature/domain-value-objects

# Create new entities branch
git checkout -b feature/domain-entities
```

#### 2.1 Company Entity (Day 2)
- [ ] **Create `src/domain/entities/company.py`**
  ```python
  class Company:
      """SEC-registered company entity"""
      def __init__(self, 
                   id: UUID,
                   cik: CIK,
                   name: str,
                   ticker: Optional[Ticker] = None,
                   sic_code: Optional[str] = None,
                   sic_description: Optional[str] = None,
                   is_active: bool = True,
                   metadata: Dict[str, Any] = None)
      
      # Business methods
      def update_ticker(self, ticker: Ticker) -> None
      def validate_cik_format(self) -> None
      def is_financial_company(self) -> bool
      def get_industry_sector(self) -> Optional[str]
      def mark_as_inactive(self) -> None
  ```

#### 2.2 Filing Entity (Day 2)
- [ ] **Create `src/domain/entities/filing.py`**
  ```python
  class Filing:
      """SEC filing entity"""
      def __init__(self,
                   id: UUID,
                   company_id: UUID,
                   accession_number: AccessionNumber,
                   filing_type: FilingType,
                   filing_date: FilingDate,
                   period_end_date: Optional[date] = None,
                   processing_status: ProcessingStatus = ProcessingStatus.PENDING,
                   file_urls: Dict[str, str] = None,
                   metadata: Dict[str, Any] = None)
      
      # Business methods
      def mark_as_processed(self) -> None
      def mark_as_failed(self, error: str) -> None
      def is_annual_report(self) -> bool
      def is_quarterly_report(self) -> bool
      def get_primary_document_url(self) -> Optional[str]
      def can_be_processed(self) -> bool
  ```

#### 2.3 Financial Statement Entities (Day 3)
- [ ] **Create `src/domain/entities/financial_statement.py`**
  ```python
  class FinancialStatement:
      """Base financial statement"""
      def __init__(self,
                   id: UUID,
                   filing_id: UUID,
                   statement_type: str,
                   period: FinancialPeriod,
                   line_items: List[FinancialLineItem])
      
      def get_total_assets(self) -> Optional[Money]
      def get_line_item(self, concept: str) -> Optional[FinancialLineItem]
      
  class BalanceSheet(FinancialStatement):
      def __init__(self, **kwargs)
      def get_current_assets(self) -> Optional[Money]
      def get_current_liabilities(self) -> Optional[Money]
      def get_stockholders_equity(self) -> Optional[Money]
      
  class IncomeStatement(FinancialStatement):
      def __init__(self, **kwargs)
      def get_revenue(self) -> Optional[Money]
      def get_net_income(self) -> Optional[Money]
      def get_operating_income(self) -> Optional[Money]
      
  class CashFlowStatement(FinancialStatement):
      def __init__(self, **kwargs)
      def get_operating_cash_flow(self) -> Optional[Money]
      def get_investing_cash_flow(self) -> Optional[Money]
      def get_financing_cash_flow(self) -> Optional[Money]
  ```

- [ ] **Create `src/domain/entities/financial_line_item.py`**
  ```python
  class FinancialLineItem:
      """Individual line item in financial statement"""
      def __init__(self,
                   concept: str,
                   label: str,
                   value: Money,
                   context: str,
                   unit: str = "USD")
  ```

#### 2.4 XBRL Fact Entity (Day 3)
- [ ] **Create `src/domain/entities/xbrl_fact.py`**
  ```python
  class XBRLFact:
      """XBRL fact representation"""
      def __init__(self,
                   id: UUID,
                   filing_id: UUID,
                   concept: str,
                   value: str,
                   context: str,
                   unit: Optional[str] = None,
                   decimals: Optional[int] = None,
                   period: Optional[FinancialPeriod] = None)
      
      def get_numeric_value(self) -> Optional[Decimal]
      def is_monetary(self) -> bool
      def get_standardized_concept(self) -> str
  ```

#### 2.5 Analysis Entity (Day 3)
- [ ] **Create `src/domain/entities/analysis.py`**
  ```python
  class AnalysisType(str, Enum):
      FINANCIAL_SUMMARY = "financial_summary"
      RISK_ANALYSIS = "risk_analysis"
      RATIO_ANALYSIS = "ratio_analysis"
      
  class Analysis:
      """Analysis result entity"""
      def __init__(self,
                   id: UUID,
                   filing_id: UUID,
                   analysis_type: AnalysisType,
                   created_by: UUID,
                   results: Dict[str, Any],
                   llm_provider: Optional[str] = None,
                   confidence_score: Optional[float] = None,
                   metadata: Dict[str, Any] = None)
      
      def is_high_confidence(self) -> bool
      def get_summary(self) -> str
      def add_insight(self, key: str, value: Any) -> None
  ```

### **Day 4: Repository Interfaces**
**Branch**: `feature/domain-repositories`

#### 4.1 Base Repository
- [ ] **Create `src/domain/repositories/base.py`**
  ```python
  class BaseRepository(ABC):
      """Abstract base repository"""
      
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

#### 4.4 Financial Data Repository
- [ ] **Create `src/domain/repositories/financial_data_repository.py`**
  ```python
  class FinancialDataRepository(BaseRepository):
      """Financial data access interface"""
      
      @abstractmethod
      async def save_financial_statement(self, 
                                        statement: FinancialStatement) -> None
      
      @abstractmethod
      async def find_statements_by_filing(self, 
                                         filing_id: UUID) -> List[FinancialStatement]
      
      @abstractmethod
      async def save_xbrl_facts(self, facts: List[XBRLFact]) -> None
      
      @abstractmethod
      async def find_xbrl_facts_by_filing(self, 
                                         filing_id: UUID) -> List[XBRLFact]
  ```

#### 4.5 Analysis Repository  
- [ ] **Create `src/domain/repositories/analysis_repository.py`**
  ```python
  class AnalysisRepository(BaseRepository):
      """Analysis data access interface"""
      
      @abstractmethod
      async def find_by_filing(self, filing_id: UUID) -> List[Analysis]
      
      @abstractmethod
      async def find_by_type(self, 
                            analysis_type: AnalysisType) -> List[Analysis]
      
      @abstractmethod
      async def find_by_user(self, user_id: UUID) -> List[Analysis]
  ```

### **Day 5: Domain Services & Events**
**Branch**: `feature/domain-services`

#### 5.1 Domain Services
- [ ] **Create `src/domain/services/filing_processor.py`**
  ```python
  class FilingProcessor:
      """Filing processing business logic"""
      
      def __init__(self, 
                   filing_repo: FilingRepository,
                   financial_repo: FinancialDataRepository)
      
      async def process_filing(self, filing: Filing) -> None
      async def validate_filing_data(self, filing: Filing) -> bool
      async def extract_financial_statements(self, filing: Filing) -> List[FinancialStatement]
      async def mark_processing_complete(self, filing: Filing) -> None
  ```

- [ ] **Create `src/domain/services/financial_calculator.py`**
  ```python
  class FinancialCalculator:
      """Financial analysis calculations"""
      
      def calculate_current_ratio(self, 
                                 balance_sheet: BalanceSheet) -> Optional[float]
      def calculate_debt_to_equity(self, 
                                  balance_sheet: BalanceSheet) -> Optional[float]
      def calculate_roa(self, 
                       income_statement: IncomeStatement,
                       balance_sheet: BalanceSheet) -> Optional[float]
      def calculate_roe(self, 
                       income_statement: IncomeStatement,
                       balance_sheet: BalanceSheet) -> Optional[float]
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

### Entities (Day 2-3)
- [ ] Business logic encapsulated in entities
- [ ] No infrastructure dependencies
- [ ] Proper state management
- [ ] Domain invariants enforced
- [ ] Rich business methods

### Repository Interfaces (Day 4)
- [ ] Abstract base classes defined
- [ ] Database-agnostic interfaces
- [ ] Async/await support
- [ ] Proper method signatures
- [ ] Documentation strings

### Domain Services (Day 5)
- [ ] Business logic not belonging to entities
- [ ] Repository dependencies injected
- [ ] Domain events published
- [ ] Exception handling
- [ ] Unit tests written

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
- **Phase 2 Progress**: 25% complete (Day 1 of 5 days)
- **Value Objects**: 8/8 implemented with full test coverage
- **Next Step**: Begin Day 2-3 entity implementation
- **Branch Status**: `feature/domain-value-objects` ready to merge

## EdgarTools Integration Notes

Reference Context7 Library ID: `/dgunning/edgartools` for:
- Company and Filing entity patterns
- XBRL fact structure
- Financial statement organization
- Business rule validation
- SEC compliance requirements

All domain models should align with edgartools concepts while maintaining clean architecture principles.