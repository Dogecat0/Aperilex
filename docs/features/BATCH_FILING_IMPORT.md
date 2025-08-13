# Batch Filing Import Feature

The Batch Filing Import feature provides a robust system for importing SEC filings in bulk from the SEC Edgar database. This feature enables efficient data collection for multiple companies and filing types while respecting SEC rate limits and ensuring data integrity.

## Overview

The batch import system allows users to:
- Import filings for multiple companies simultaneously
- Filter by specific filing types (10-K, 10-Q, 8-K, etc.)
- Apply date range filters for historical analysis
- Process imports asynchronously with progress tracking
- Handle rate limiting and errors gracefully
- Support both ticker symbols and CIK identifiers

## Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CLI Script                        │
│            (scripts/import_filings.py)              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              ImportFilingsCommand                   │
│         (Command Schema & Validation)               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          ImportFilingsCommandHandler                │
│          (Command Processing Logic)                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│        BackgroundTaskCoordinator                    │
│        (Task Queue Management)                      │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           Celery Background Tasks                   │
│    (batch_import_filings_task & subtasks)          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Edgar Service & Repositories           │
│        (Data Fetching & Persistence)                │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **Command Creation**: User initiates import via CLI or API
2. **Validation**: Command validates parameters (identifiers, dates, filing types)
3. **Handler Processing**: Handler resolves tickers to CIKs and prepares import
4. **Task Queuing**: Background tasks are queued via Celery
5. **Parallel Processing**: Companies are processed in chunks with rate limiting
6. **Data Persistence**: Filings are stored in PostgreSQL database
7. **Result Aggregation**: Task results are collected and returned

## Usage

### Command Line Interface

The primary interface for batch imports is the CLI script:

```bash
# Basic import for multiple companies
python scripts/import_filings.py --tickers AAPL,MSFT,GOOGL

# Import using CIK numbers
python scripts/import_filings.py --ciks 320193,789019,1652044

# Specify filing types and limits
python scripts/import_filings.py --tickers AAPL --filing-types 10-K,10-Q --limit 5

# Date range filtering
python scripts/import_filings.py --tickers TSLA \
    --start-date 2023-01-01 --end-date 2023-12-31

# Dry run mode for preview
python scripts/import_filings.py --tickers AAPL,MSFT --dry-run --verbose
```

### Programmatic Usage

For integration into applications:

```python
from src.application.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy
)
from src.application.commands.handlers.import_filings_handler import (
    ImportFilingsCommandHandler
)

# Create command
command = ImportFilingsCommand(
    companies=["AAPL", "MSFT", "0000320193"],
    filing_types=["10-K", "10-Q"],
    limit_per_company=5,
    import_strategy=ImportStrategy.BY_COMPANIES
)

# Validate
command.validate()

# Execute via handler
handler = ImportFilingsCommandHandler(
    background_task_coordinator=coordinator,
    filing_repository=filing_repo,
    company_repository=company_repo,
    edgar_service=edgar_service
)

result = await handler.handle(command)
print(f"Task ID: {result.task_id}, Status: {result.status}")
```

## Import Strategies

### BY_COMPANIES Strategy

The default strategy for importing filings for specific companies:

**When to use:**
- You know exactly which companies you want to analyze
- You need the most recent filings for specific entities
- You want efficient, targeted data collection

**Requirements:**
- Must provide `companies` list (tickers or CIKs)
- Optional: `start_date`, `end_date` for additional filtering

**Example:**
```python
command = ImportFilingsCommand(
    companies=["AAPL", "MSFT"],
    filing_types=["10-K", "10-Q"],
    limit_per_company=4,
    import_strategy=ImportStrategy.BY_COMPANIES
)
```

### BY_DATE_RANGE Strategy

Strategy for importing all filings within a specific date range:

**When to use:**
- You need comprehensive data for a specific time period
- You're conducting historical or trend analysis
- You want to capture market-wide events

**Requirements:**
- Must provide both `start_date` and `end_date`
- Optional: `companies` list to filter within date range

**Example:**
```python
command = ImportFilingsCommand(
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    filing_types=["8-K"],
    import_strategy=ImportStrategy.BY_DATE_RANGE
)
```

## Supported Filing Types

The system supports all major SEC filing types:

| Filing Type | Description | Use Case |
|------------|-------------|----------|
| **10-K** | Annual report | Comprehensive yearly analysis |
| **10-Q** | Quarterly report | Quarterly performance tracking |
| **8-K** | Current report | Material events and changes |
| **DEF 14A** | Proxy statement | Governance and compensation |
| **S-1** | Registration statement | IPO analysis |
| **20-F** | Foreign company annual report | International companies |
| **13F** | Institutional holdings | Investment tracking |
| **3, 4, 5** | Insider trading forms | Insider activity analysis |

Default filing types: `["10-K", "10-Q"]`

## Rate Limiting and Performance

### SEC Compliance

The system implements SEC-compliant rate limiting:
- Maximum 10 requests per second to SEC Edgar
- Automatic exponential backoff on rate limit errors
- Jitter added to prevent thundering herd problems
- Chunked processing to manage memory usage

### Performance Optimization

```python
# Chunking configuration
chunk_size = 5  # Process 5 companies in parallel
jitter_delay = random.uniform(0.05, 0.15)  # 50-150ms
base_delay = 1.0  # 1 second between chunks

# Backoff on failures
if chunk_failures > 0:
    failure_rate = chunk_failures / len(chunk)
    backoff_multiplier = min(4.0, 1 + failure_rate * 3)
    delay *= backoff_multiplier
```

### Performance Metrics

Expected performance for typical imports:
- **Small batch** (5 companies, 2 filing types): ~30 seconds
- **Medium batch** (20 companies, 2 filing types): ~2-3 minutes
- **Large batch** (50 companies, 3 filing types): ~10-15 minutes

## Error Handling

### Validation Errors

The command validates all parameters before execution:

```python
try:
    command.validate()
except ValueError as e:
    # Handle validation errors
    # - Invalid company identifiers
    # - Invalid date ranges
    # - Unsupported filing types
    # - Out-of-range limits
    print(f"Validation error: {e}")
```

### Task Failures

Individual company failures don't stop the batch:

```json
{
  "task_id": "batch-import-123",
  "total_companies": 10,
  "processed_companies": 8,
  "failed_companies": 2,
  "failed_companies_details": [
    {
      "company": "INVALID",
      "error": "Company not found",
      "chunk": 1
    }
  ],
  "status": "completed"
}
```

### Recovery Mechanisms

- **Automatic retry**: Failed tasks are retried with exponential backoff
- **Partial success**: Batch continues even if individual companies fail
- **Detailed logging**: All failures are logged with context
- **Progress tracking**: Real-time status updates during processing

## Background Task Details

### Main Task: batch_import_filings_task

The primary orchestration task that manages the batch import:

**Parameters:**
- `companies`: List of company identifiers
- `filing_types`: List of filing types to import
- `limit_per_company`: Maximum filings per company
- `start_date`: Optional start date filter
- `end_date`: Optional end date filter
- `chunk_size`: Number of companies to process in parallel

**Returns:**
```python
{
    "task_id": str,
    "total_companies": int,
    "processed_companies": int,
    "failed_companies": int,
    "total_filings_created": int,
    "total_filings_existing": int,
    "processing_time_seconds": float,
    "chunks_processed": int,
    "success_rate": float,
    "failed_companies_details": List[dict],
    "status": str
}
```

### Subtask: fetch_company_filings_task

Individual company filing fetch task:

**Parameters:**
- `cik`: Company CIK identifier
- `form_types`: List of form types
- `limit`: Maximum number of filings

**Returns:**
```python
{
    "task_id": str,
    "cik": str,
    "company_name": str,
    "total_filings_processed": int,
    "created_count": int,
    "updated_count": int,
    "status": str
}
```

## Database Schema

### Filing Entity

Imported filings are stored with the following structure:

```python
Filing:
    id: UUID
    company_id: UUID
    accession_number: AccessionNumber
    filing_type: FilingType
    filing_date: datetime
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

### Company Entity

Companies are automatically created if not existing:

```python
Company:
    id: UUID
    cik: CIK
    ticker: Ticker (optional)
    name: str
    industry: str (optional)
    created_at: datetime
    updated_at: datetime
```

## Best Practices

### 1. Use Appropriate Strategies

- Use `BY_COMPANIES` for targeted analysis of specific companies
- Use `BY_DATE_RANGE` for market-wide or historical analysis

### 2. Optimize Batch Sizes

- Start with smaller batches (5-10 companies) for testing
- Increase batch sizes gradually based on system capacity
- Monitor rate limiting and adjust chunk_size if needed

### 3. Handle Identifiers Properly

- Prefer CIKs over tickers for reliability
- Validate identifiers before large imports
- Use dry-run mode to preview imports

### 4. Monitor Progress

- Use verbose logging for large imports
- Check task status via task_id
- Review failed_companies_details for issues

### 5. Respect Rate Limits

- Don't run multiple large imports simultaneously
- Allow time between consecutive imports
- Monitor SEC compliance in logs

## Monitoring and Logging

### Log Levels

```python
# INFO: High-level progress
INFO: Starting batch import task for 10 companies

# DEBUG: Detailed operations (--verbose)
DEBUG: Processing chunk 1/2 with 5 companies
DEBUG: Resolved ticker AAPL to CIK 0000320193

# WARNING: Non-critical issues
WARNING: Invalid company identifier: INVALID

# ERROR: Failures requiring attention
ERROR: Task failed for company AAPL: Connection timeout
```

### Progress Tracking

Monitor import progress through:
1. Console output with --verbose flag
2. Task status via task_id
3. Database queries for imported filings
4. Celery flower dashboard (if configured)

## Troubleshooting

### Common Issues

**1. "Invalid company identifier" error**
- Verify ticker symbols are correct (e.g., AAPL not Apple)
- Ensure CIKs are numeric (e.g., 320193)
- Check for typos in identifiers

**2. "start_date cannot be in the future" error**
- Use YYYY-MM-DD format for dates
- Ensure dates are in the past
- Verify system clock is correct

**3. Rate limiting errors**
- Reduce chunk_size parameter
- Add delays between imports
- Check SEC compliance settings

**4. Connection timeouts**
- Verify internet connectivity
- Check Edgar service availability
- Review proxy/firewall settings

**5. Memory issues with large batches**
- Reduce limit_per_company
- Process companies in smaller batches
- Monitor system resources

### Debug Commands

```bash
# Test with single company
python scripts/import_filings.py --tickers AAPL --limit 1 --verbose

# Validate without importing
python scripts/import_filings.py --tickers AAPL --dry-run

# Check specific filing types
python scripts/import_filings.py --tickers MSFT --filing-types 8-K --limit 2
```

## Integration Examples

### With Analysis Pipeline

```python
# Import filings then analyze
from src.application.schemas.commands import (
    ImportFilingsCommand,
    CreateAnalysisCommand
)

# Step 1: Import filings
import_cmd = ImportFilingsCommand(
    companies=["AAPL"],
    filing_types=["10-K"],
    limit_per_company=1
)
import_result = await import_handler.handle(import_cmd)

# Step 2: Wait for import completion
await wait_for_task_completion(import_result.task_id)

# Step 3: Create analysis
analysis_cmd = CreateAnalysisCommand(
    ticker="AAPL",
    filing_type="10-K"
)
analysis_result = await analysis_handler.handle(analysis_cmd)
```

### With Scheduled Jobs

```python
# Celery periodic task for regular imports
from celery.schedules import crontab

@celery_app.task
def scheduled_import():
    """Import latest filings for watchlist companies."""
    command = ImportFilingsCommand(
        companies=WATCHLIST_COMPANIES,
        filing_types=["10-K", "10-Q", "8-K"],
        limit_per_company=2
    )
    return import_filings_task.delay(command.get_import_parameters())

# Schedule for daily execution
celery_app.conf.beat_schedule = {
    'daily-filing-import': {
        'task': 'scheduled_import',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

## Future Enhancements

Planned improvements for the batch import feature:

1. **Real-time Progress Updates**
   - WebSocket support for live progress tracking
   - Granular progress per company
   - ETA calculations

2. **Advanced Filtering**
   - Industry-based imports
   - Market cap filtering
   - Insider trading thresholds

3. **Import Profiles**
   - Save and reuse import configurations
   - Template-based imports
   - Scheduled import profiles

4. **Enhanced Error Recovery**
   - Automatic resume for interrupted imports
   - Selective retry for failed companies
   - Error pattern detection

5. **Performance Improvements**
   - Adaptive chunk sizing
   - Predictive rate limiting
   - Caching for repeated imports

## Related Documentation

- [ImportFilingsCommand API Reference](../api/commands/import_filings.md)
- [Background Tasks Documentation](../infrastructure/background_tasks.md)
- [Edgar Service Integration](../infrastructure/edgar_service.md)
- [CLI Tools Guide](../../scripts/README.md)
