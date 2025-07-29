// Central API export
export * from './types'
export * from './client'
export { companiesApi } from './companies'
export { filingsApi } from './filings'
export { analysesApi } from './analyses'
export { tasksApi } from './tasks'
export { healthApi } from './health'

// Re-export as a single API object for convenience
import { companiesApi } from './companies'
import { filingsApi } from './filings'
import { analysesApi } from './analyses'
import { tasksApi } from './tasks'
import { healthApi } from './health'

export const aperilexApi = {
  companies: companiesApi,
  filings: filingsApi,
  analyses: analysesApi,
  tasks: tasksApi,
  health: healthApi,
}
