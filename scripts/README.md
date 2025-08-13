# Development Scripts

This directory contains development scripts for generating analysis samples and validating API integration without the overhead of test infrastructure.

## Scripts Overview

### 1. `generate_analysis_samples.py`
Generates comprehensive analysis samples using real Edgar and OpenAI API calls. This script replaces the expensive parts of `test_infrastructure.py` for development purposes.

**Features:**
- Full filing analysis with 28+ sub-sections
- Individual section analysis
- Real SEC filing content extraction
- Schema-validated analysis responses
- Progress tracking and error handling
- Analysis summary generation

**Usage:**
```bash
# Generate comprehensive analysis for Microsoft 10-K
python scripts/generate_analysis_samples.py --ticker MSFT --form 10-K

# Generate analysis for Apple 10-Q
python scripts/generate_analysis_samples.py --ticker AAPL --form 10-Q

# Generate only Business section analysis
python scripts/generate_analysis_samples.py --ticker MSFT --section "Item 1 - Business"

# Validate API connectivity only
python scripts/generate_analysis_samples.py --validate-only
```

**Environment Variables:**
- `OPENAI_API_KEY` (required): Your OpenAI API key
- `OPENAI_BASE_URL` (optional): OpenAI base URL (defaults to https://api.openai.com/v1)

### 2. `import_filings.py`
Management command for batch importing SEC filings using the ImportFilingsCommand and background task system.

**Features:**
- Batch import SEC filings by ticker or CIK
- Support for multiple filing types (10-K, 10-Q, 8-K, etc.)
- Date range filtering for targeted imports
- Configurable limits per company
- Dry-run mode for testing
- Verbose logging and progress tracking
- Command validation and error handling

**Usage:**
```bash
# Import recent filings for specific companies
poetry run python scripts/import_filings.py --tickers AAPL,MSFT,GOOGL

# Import using CIK numbers instead of tickers
poetry run python scripts/import_filings.py --ciks 320193,789019,1652044

# Import specific filing types with custom limits
poetry run python scripts/import_filings.py --tickers AAPL --filing-types 10-K,10-Q --limit 2

# Import filings within specific date range
poetry run python scripts/import_filings.py --tickers TSLA --start-date 2023-01-01 --end-date 2023-12-31

# Test import parameters without actually importing (dry run)
poetry run python scripts/import_filings.py --tickers AAPL --dry-run --verbose

# Get help and see all options
poetry run python scripts/import_filings.py --help
```

**Command Line Arguments:**
- `--tickers`: Comma-separated list of ticker symbols
- `--ciks`: Comma-separated list of CIK numbers (alternative to tickers)
- `--filing-types`: Filing types to import (default: 10-K,10-Q)
- `--limit`: Maximum filings per company (default: 4)
- `--start-date`: Start date filter (YYYY-MM-DD format)
- `--end-date`: End date filter (YYYY-MM-DD format)
- `--dry-run`: Show what would be imported without importing
- `--verbose`: Enable detailed logging

**Supported Filing Types:**
- 10-K, 10-K/A: Annual reports
- 10-Q, 10-Q/A: Quarterly reports
- 8-K, 8-K/A: Current reports
- DEF 14A, DEFA14A: Proxy statements
- S-1, S-3, S-4: Registration statements
- 13F, 3, 4, 5: Ownership reports

### 3. `validate_api_integration.py`
Lightweight validation of API integration and schema compatibility without expensive analysis operations.

**Features:**
- Edgar API connectivity and data structure validation
- OpenAI API connectivity and response validation
- Pydantic schema definition validation
- Factory function testing
- Comprehensive validation reporting

**Usage:**
```bash
# Full validation suite
python scripts/validate_api_integration.py

# Quick validation (minimal API calls)
python scripts/validate_api_integration.py --quick

# Validate only schema definitions (no API calls)
python scripts/validate_api_integration.py --schemas-only
```

## Output

Both scripts generate output in the `test_results/` directory:

### Generated Files
- `filing_analysis_[TICKER]_[FORM]_[TIMESTAMP].json` - Comprehensive filing analysis
- `filing_sections_[TICKER]_[FORM]_[TIMESTAMP].json` - Raw extracted filing sections
- `section_analysis_[SECTION_NAME].json` - Individual section analysis
- `analysis_summary_[TIMESTAMP].json` - Human-readable analysis summary
- `validation_results_[TIMESTAMP].json` - API validation results

### File Structure Examples

**Comprehensive Filing Analysis:**
```json
{
  "filing_summary": "Executive summary of the filing...",
  "key_insights": ["Insight 1", "Insight 2", ...],
  "financial_highlights": ["Highlight 1", ...],
  "section_analyses": [
    {
      "section_name": "Business",
      "sub_sections": [
        {
          "sub_section_name": "Operational Overview",
          "schema_type": "OperationalOverview",
          "analysis": { ... }
        }
      ]
    }
  ],
  "confidence_score": 0.95,
  "total_processing_time_ms": 46021
}
```

**Section Analysis:**
```json
{
  "section_name": "Item 1 - Business",
  "section_summary": "Summary of business operations...",
  "overall_sentiment": 0.85,
  "sub_sections": [
    {
      "sub_section_name": "Operational Overview",
      "schema_type": "OperationalOverview",
      "processing_time_ms": 1245,
      "analysis": {
        "description": "Business description...",
        "industry_classification": "Technology",
        "primary_markets": ["Cloud Computing", "Software"]
      }
    }
  ]
}
```

## Development Workflow

### 1. Initial Setup
```bash
# Set environment variables
export OPENAI_API_KEY="your-api-key-here"

# Validate setup
python scripts/validate_api_integration.py --schemas-only
```

### 2. API Validation
```bash
# Quick connectivity check
python scripts/validate_api_integration.py --quick

# Full validation
python scripts/validate_api_integration.py
```

### 3. Generate Analysis Samples
```bash
# Generate samples for development
python scripts/generate_analysis_samples.py --ticker MSFT

# Test specific sections
python scripts/generate_analysis_samples.py --section "Item 1A - Risk Factors"
```

### 4. Development Testing
Use the generated samples in unit tests with enhanced mock fixtures:
```python
# In your tests
def test_analysis_with_realistic_data(realistic_filing_analysis):
    # Use realistic fixture data instead of simple mocks
    assert realistic_filing_analysis["confidence_score"] == 0.95
    assert len(realistic_filing_analysis["section_analyses"]) >= 6
```

## Cost Management

### API Usage Guidelines
- **Edgar API**: Free but rate-limited (10 requests/second)
- **OpenAI API**: Paid service - comprehensive analysis costs ~$0.50-2.00 per filing
- **Section Analysis**: Individual sections cost ~$0.05-0.20 each

### Cost-Effective Development
1. Use `--validate-only` for connectivity testing
2. Use `validate_api_integration.py --quick` for schema validation
3. Generate samples only when needed for development
4. Use realistic mock fixtures for unit tests instead of real API calls

## Integration with Testing

### Unit Tests
- Use enhanced mock fixtures from `tests/conftest.py`
- Mock external API calls using realistic response structures
- Validate business logic without API costs

### Integration Tests
- Use pytest markers to control external API usage:
  ```bash
  # Skip external API tests
  pytest -m "not external_api"

  # Run only integration tests
  pytest -m "integration"
  ```

### Example Test Organization
```bash
# Fast unit tests (no external APIs)
pytest tests/unit/ -m "not external_api"

# Integration tests with mocks
pytest tests/integration/ -m "not external_api"

# Full integration tests (real APIs)
pytest tests/integration/ -m "external_api"
```

## Troubleshooting

### Common Issues

**1. API Key Issues**
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Validate API key
python scripts/validate_api_integration.py --quick
```

**2. Edgar API Rate Limiting**
- Add delays between requests if getting rate limit errors
- Edgar API allows 10 requests/second maximum

**3. Schema Validation Errors**
```bash
# Test schema definitions only
python scripts/validate_api_integration.py --schemas-only
```

**4. Network/Connectivity Issues**
- Use `--validate-only` flag to test connectivity
- Check firewall and proxy settings

### Error Codes
- Exit 0: Success
- Exit 1: Validation/generation failed
- Exit 130: Interrupted by user (Ctrl+C)

## Contributing

When adding new scripts:
1. Follow the existing pattern for argument parsing
2. Include comprehensive error handling
3. Add progress indicators for long-running operations
4. Save results to `test_results/` directory
5. Update this README with usage examples
