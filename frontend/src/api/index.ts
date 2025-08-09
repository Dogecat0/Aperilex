// Central API export
export * from './types'
export * from './client'
export { companiesApi, type CompanyAnalysesFilters, type CompanyFilingsFilters } from './companies'
export { filingsApi } from './filings'
export { analysesApi } from './analyses'
export { tasksApi } from './tasks'
export { healthApi } from './health'

// Export services
export { filingService, FilingService } from './services/FilingService'

// Re-export as a single API object for convenience
import { companiesApi } from './companies'
import { filingsApi } from './filings'
import { analysesApi } from './analyses'
import { tasksApi } from './tasks'
import { healthApi } from './health'
import { filingService } from './services/FilingService'

export const aperilexApi = {
  companies: companiesApi,
  filings: filingsApi,
  analyses: analysesApi,
  tasks: tasksApi,
  health: healthApi,
  filingService,
}
