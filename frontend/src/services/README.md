# Company API Services

This directory contains high-level service classes that provide business logic for interacting with the Aperilex API.

## CompanyService

The `CompanyService` class provides methods for company-related operations with built-in validation, error handling, and business logic.

### Usage Examples

```typescript
import { companyService } from '@/services'

// Basic company information
const company = await companyService.getCompany('AAPL')

// Company with recent analyses included
const companyWithAnalyses = await companyService.getCompanyWithAnalyses('AAPL')

// Get company analyses with filters
const analyses = await companyService.getCompanyAnalyses('AAPL', {
  page: 1,
  page_size: 10,
  analysis_type: 'FINANCIAL_FOCUSED',
  start_date: '2023-01-01',
  end_date: '2023-12-31',
})

// Get most recent analysis
const recentAnalysis = await companyService.getMostRecentAnalysis('AAPL')

// Check if company exists
const exists = await companyService.companyExists('AAPL')
```

### React Hooks Integration

The services work seamlessly with React Query hooks:

```typescript
import { useCompany, useCompanyAnalyses } from '@/hooks'

function CompanyProfile({ ticker }: { ticker: string }) {
  const { data: company, isLoading } = useCompany(ticker, {
    includeRecentAnalyses: true,
  })

  const { data: analyses } = useCompanyAnalyses(ticker, {
    page: 1,
    page_size: 10,
    analysis_type: 'COMPREHENSIVE',
  })

  // Component rendering...
}
```

### Features

- **Input Validation**: Automatic ticker normalization and validation
- **Error Handling**: User-friendly error messages with context
- **Type Safety**: Full TypeScript support with proper types
- **Flexible Filtering**: Support for pagination, date ranges, and analysis types
- **Business Logic**: High-level methods like `getMostRecentAnalysis` and `companyExists`

### API Methods

| Method                   | Description                         | Parameters                |
| ------------------------ | ----------------------------------- | ------------------------- |
| `getCompany`             | Get company information             | `ticker`, `options?`      |
| `getCompanyAnalyses`     | Get company analyses with filtering | `ticker`, `options?`      |
| `getMostRecentAnalysis`  | Get the most recent analysis        | `ticker`, `analysisType?` |
| `companyExists`          | Check if company exists             | `ticker`                  |
| `getCompanyWithAnalyses` | Get company with recent analyses    | `ticker`                  |

All methods include automatic ticker validation and normalization to uppercase.
