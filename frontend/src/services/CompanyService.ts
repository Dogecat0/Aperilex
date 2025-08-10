import {
  aperilexApi,
  type CompanyResponse,
  type AnalysisResponse,
  type CompanyAnalysesFilters,
  type PaginatedResponse,
} from '@/api'

export interface GetCompanyOptions {
  includeRecentAnalyses?: boolean
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface GetCompanyAnalysesOptions extends CompanyAnalysesFilters {
  // Additional service-level options can be added here in the future
  // This interface is currently empty but extends CompanyAnalysesFilters
}

/**
 * CompanyService provides high-level business logic for company-related operations.
 * It wraps the low-level API calls with additional error handling, validation, and business logic.
 */
export class CompanyService {
  /**
   * Get company information by ticker symbol
   * @param ticker - Company ticker symbol (e.g., 'AAPL', 'MSFT')
   * @param options - Optional parameters for the request
   * @returns Promise resolving to company data
   * @throws Error with user-friendly message on failure
   */
  async getCompany(ticker: string, options: GetCompanyOptions = {}): Promise<CompanyResponse> {
    try {
      // Validate ticker format
      if (!ticker || typeof ticker !== 'string' || ticker.trim().length === 0) {
        throw new Error('Ticker symbol is required and must be a string')
      }

      // Normalize ticker to uppercase
      const normalizedTicker = ticker.trim().toUpperCase()

      if (normalizedTicker.length > 10) {
        throw new Error('Ticker symbol must be between 1 and 10 characters')
      }

      return await aperilexApi.companies.getCompany(normalizedTicker, options.includeRecentAnalyses)
    } catch (error) {
      // Re-throw with more context for debugging
      if (error instanceof Error) {
        throw new Error(`Failed to fetch company data for ${ticker}: ${error.message}`)
      }
      throw new Error(`Failed to fetch company data for ${ticker}: Unknown error`)
    }
  }

  /**
   * Get analyses for a specific company with optional filtering and pagination
   * @param ticker - Company ticker symbol
   * @param options - Optional filters and pagination parameters
   * @returns Promise resolving to analyses data (array or paginated response)
   * @throws Error with user-friendly message on failure
   */
  async getCompanyAnalyses(
    ticker: string,
    options: GetCompanyAnalysesOptions = {}
  ): Promise<PaginatedResponse<AnalysisResponse> | AnalysisResponse[]> {
    try {
      // Validate ticker format
      if (!ticker || typeof ticker !== 'string' || ticker.trim().length === 0) {
        throw new Error('Ticker symbol is required and must be a string')
      }

      // Normalize ticker to uppercase
      const normalizedTicker = ticker.trim().toUpperCase()

      if (normalizedTicker.length > 10) {
        throw new Error('Ticker symbol must be between 1 and 10 characters')
      }

      // Validate date formats if provided
      if (options.start_date && !this.isValidDateString(options.start_date)) {
        throw new Error('start_date must be in YYYY-MM-DD format')
      }

      if (options.end_date && !this.isValidDateString(options.end_date)) {
        throw new Error('end_date must be in YYYY-MM-DD format')
      }

      // Validate date range
      if (options.start_date && options.end_date) {
        const startDate = new Date(options.start_date)
        const endDate = new Date(options.end_date)

        if (startDate > endDate) {
          throw new Error('start_date must be before or equal to end_date')
        }
      }

      // Validate pagination parameters
      if (options.page !== undefined && (options.page < 1 || !Number.isInteger(options.page))) {
        throw new Error('page must be a positive integer')
      }

      if (
        options.page_size !== undefined &&
        (options.page_size < 1 || options.page_size > 100 || !Number.isInteger(options.page_size))
      ) {
        throw new Error('page_size must be a positive integer between 1 and 100')
      }

      return await aperilexApi.companies.getCompanyAnalyses(normalizedTicker, options)
    } catch (error) {
      // Re-throw with more context for debugging
      if (error instanceof Error) {
        throw new Error(`Failed to fetch analyses for ${ticker}: ${error.message}`)
      }
      throw new Error(`Failed to fetch analyses for ${ticker}: Unknown error`)
    }
  }

  /**
   * Get the most recent analysis for a company
   * @param ticker - Company ticker symbol
   * @param analysisType - Optional filter by analysis type
   * @returns Promise resolving to the most recent analysis or null if none found
   */
  async getMostRecentAnalysis(
    ticker: string,
    analysisType?: CompanyAnalysesFilters['analysis_template']
  ): Promise<AnalysisResponse | null> {
    try {
      const analyses = await this.getCompanyAnalyses(ticker, {
        page: 1,
        page_size: 1,
        analysis_template: analysisType,
      })

      // Handle both paginated and array responses
      if (Array.isArray(analyses)) {
        return analyses.length > 0 ? analyses[0] : null
      } else {
        return analyses.items.length > 0 ? analyses.items[0] : null
      }
    } catch (error) {
      // Return null for not found errors, re-throw others
      if (error instanceof Error && error.message.includes('404')) {
        return null
      }
      throw error
    }
  }

  /**
   * Check if a company exists by ticker
   * @param ticker - Company ticker symbol
   * @returns Promise resolving to true if company exists, false otherwise
   */
  async companyExists(ticker: string): Promise<boolean> {
    try {
      await this.getCompany(ticker)
      return true
    } catch (error) {
      // Return false for not found errors, re-throw others
      if (error instanceof Error && error.message.includes('404')) {
        return false
      }
      throw error
    }
  }

  /**
   * Get company with enriched data (company info + recent analyses)
   * @param ticker - Company ticker symbol
   * @returns Promise resolving to company data with recent analyses
   */
  async getCompanyWithAnalyses(ticker: string): Promise<CompanyResponse> {
    return this.getCompany(ticker, { includeRecentAnalyses: true })
  }

  /**
   * Validate date string format (YYYY-MM-DD)
   * @private
   */
  private isValidDateString(dateString: string): boolean {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/
    if (!dateRegex.test(dateString)) {
      return false
    }

    const date = new Date(dateString)
    return (
      date instanceof Date &&
      !isNaN(date.getTime()) &&
      dateString === date.toISOString().split('T')[0]
    )
  }
}

// Export a singleton instance for convenience
export const companyService = new CompanyService()
