import { filingsApi, type FilingSearchParams } from '../filings'
import type {
  FilingResponse,
  AnalysisResponse,
  TaskResponse,
  AnalyzeFilingRequest,
  ComprehensiveAnalysisResponse,
  PaginatedResponse,
  APIError,
  FilingSearchResult,
  EdgarSearchParams,
} from '../types'

/**
 * Service class for Filing-related operations
 *
 * Provides higher-level business logic and error handling around filing operations.
 * Wraps the basic API calls with additional functionality like status polling,
 * validation, and comprehensive error handling.
 */
export class FilingService {
  /**
   * Search filings by ticker with optional filters (database search)
   *
   * @param params - Search parameters including ticker and optional filters
   * @returns Promise resolving to paginated filing results
   * @throws APIError when search fails or ticker not found
   */
  async searchFilings(params: FilingSearchParams): Promise<PaginatedResponse<FilingResponse>> {
    this.validateSearchParams(params)

    try {
      return await filingsApi.searchFilings(params)
    } catch (error) {
      throw this.handleFilingError(error, 'searching filings for ticker', params.ticker)
    }
  }

  /**
   * Search Edgar filings directly from SEC API
   *
   * This method queries the SEC Edgar database directly through our backend proxy,
   * providing access to all available filings for a company, not just those
   * previously processed by our system.
   *
   * @param params - Edgar search parameters including ticker and optional filters
   * @returns Promise resolving to paginated Edgar filing search results
   * @throws APIError when search fails or ticker not found
   */
  async searchEdgarFilings(
    params: EdgarSearchParams
  ): Promise<PaginatedResponse<FilingSearchResult>> {
    this.validateEdgarSearchParams(params)

    try {
      return await filingsApi.searchEdgarFilings(params)
    } catch (error) {
      throw this.handleFilingError(error, 'searching Edgar filings for ticker', params.ticker)
    }
  }

  /**
   * Get filing information by accession number
   *
   * @param accessionNumber - The SEC accession number (e.g., "0000320193-23-000106")
   * @returns Promise resolving to filing details with metadata
   * @throws APIError when filing not found or network issues occur
   */
  async getFiling(accessionNumber: string): Promise<FilingResponse> {
    this.validateAccessionNumber(accessionNumber)

    try {
      return await filingsApi.getFiling(accessionNumber)
    } catch (error) {
      throw this.handleFilingError(error, 'retrieving filing', accessionNumber)
    }
  }

  /**
   * Get filing information by filing ID (UUID)
   *
   * @param filingId - The filing UUID (e.g., "12345678-1234-1234-1234-123456789abc")
   * @returns Promise resolving to filing details with metadata
   * @throws APIError when filing not found or network issues occur
   */
  async getFilingById(filingId: string): Promise<FilingResponse> {
    this.validateFilingId(filingId)

    try {
      return await filingsApi.getFilingById(filingId)
    } catch (error) {
      throw this.handleFilingError(error, 'retrieving filing by ID', filingId)
    }
  }

  /**
   * Analyze a filing using LLM processing
   *
   * Initiates the analysis process and returns a task for monitoring progress.
   * The actual analysis is performed asynchronously by the backend.
   *
   * @param accessionNumber - The SEC accession number
   * @param options - Analysis configuration options
   * @returns Promise resolving to task information for tracking analysis progress
   * @throws APIError when analysis cannot be initiated
   */
  async analyzeFiling(
    accessionNumber: string,
    options?: AnalyzeFilingRequest
  ): Promise<TaskResponse> {
    this.validateAccessionNumber(accessionNumber)

    // Validate analysis options if provided
    if (options) {
      this.validateAnalysisOptions(options)
    }

    try {
      const task = await filingsApi.analyzeFiling(accessionNumber, options)
      return task
    } catch (error) {
      throw this.handleFilingError(error, 'initiating analysis for filing', accessionNumber)
    }
  }

  /**
   * Get the comprehensive analysis results for a filing
   *
   * Retrieves the full LLM-generated analysis including executive summary,
   * section breakdowns, financial insights, and risk assessments.
   *
   * @param accessionNumber - The SEC accession number
   * @returns Promise resolving to comprehensive analysis results
   * @throws APIError when analysis not found or not yet completed
   */
  async getFilingAnalysis(accessionNumber: string): Promise<AnalysisResponse> {
    this.validateAccessionNumber(accessionNumber)

    try {
      return await filingsApi.getFilingAnalysis(accessionNumber)
    } catch (error) {
      throw this.handleFilingError(error, 'retrieving analysis for filing', accessionNumber)
    }
  }

  /**
   * Get comprehensive analysis results with full detail
   *
   * Similar to getFilingAnalysis but specifically typed for the comprehensive
   * analysis response structure with all sections and subsections.
   *
   * @param accessionNumber - The SEC accession number
   * @returns Promise resolving to comprehensive analysis with full detail
   * @throws APIError when analysis not found or not yet completed
   */
  async getComprehensiveAnalysis(accessionNumber: string): Promise<ComprehensiveAnalysisResponse> {
    const analysis = await this.getFilingAnalysis(accessionNumber)

    // The backend returns the comprehensive analysis in the full_results field
    if (!analysis.full_results) {
      const error: APIError = {
        detail: 'Comprehensive analysis results not available for this filing',
        status_code: 404,
        error_code: 'ANALYSIS_INCOMPLETE',
      }
      throw error
    }

    // Transform the analysis response to match the comprehensive structure
    return {
      filing_summary: analysis.filing_summary || '',
      executive_summary: analysis.executive_summary || '',
      key_insights: analysis.key_insights || [],
      financial_highlights: analysis.financial_highlights || [],
      risk_factors: analysis.risk_factors || [],
      opportunities: analysis.opportunities || [],
      confidence_score: analysis.confidence_score || 0,
      section_analyses:
        analysis.full_results.sections?.map((section) => ({
          section_name: section.section_name,
          section_summary: section.summary || '',
          consolidated_insights: [],
          overall_sentiment: 0, // Will be properly mapped from backend data
          critical_findings: [],
          sub_sections: [],
          processing_time_ms: null,
          sub_section_count: 0,
        })) || [],
      total_sections_analyzed: analysis.sections_analyzed || 0,
      total_sub_sections_analyzed: 0,
      total_processing_time_ms: analysis.processing_time_seconds
        ? analysis.processing_time_seconds * 1000
        : null,
      filing_type: '', // Will be populated from filing data
      company_name: '', // Will be populated from filing data
      analysis_timestamp: analysis.created_at,
    }
  }

  /**
   * Check if a filing has been analyzed
   *
   * @param accessionNumber - The SEC accession number
   * @returns Promise resolving to boolean indicating if analysis exists
   */
  async hasAnalysis(accessionNumber: string): Promise<boolean> {
    try {
      await this.getFilingAnalysis(accessionNumber)
      return true
    } catch (error) {
      const apiError = error as APIError
      if (apiError.status_code === 404) {
        return false
      }
      throw error
    }
  }

  /**
   * Get filing status with analysis information
   *
   * Combines filing metadata with analysis status for a complete view.
   *
   * @param accessionNumber - The SEC accession number
   * @returns Promise resolving to enriched filing status
   */
  async getFilingStatus(accessionNumber: string): Promise<
    FilingResponse & {
      has_analysis: boolean
      analysis_date?: string
    }
  > {
    const filing = await this.getFiling(accessionNumber)
    const hasAnalysis = await this.hasAnalysis(accessionNumber)

    let analysisDate: string | undefined
    if (hasAnalysis) {
      try {
        const analysis = await this.getFilingAnalysis(accessionNumber)
        analysisDate = analysis.created_at
      } catch {
        // Ignore errors when fetching analysis date
      }
    }

    return {
      ...filing,
      has_analysis: hasAnalysis,
      analysis_date: analysisDate,
    }
  }

  /**
   * Poll for analysis completion
   *
   * Useful for monitoring the progress of a filed analysis task.
   *
   * @param accessionNumber - The SEC accession number
   * @param pollIntervalMs - Polling interval in milliseconds (default: 5000)
   * @param maxAttempts - Maximum polling attempts (default: 24, ~2 minutes)
   * @returns Promise resolving when analysis is complete
   */
  async pollForAnalysisCompletion(
    accessionNumber: string,
    pollIntervalMs: number = 5000,
    maxAttempts: number = 24
  ): Promise<AnalysisResponse> {
    let attempts = 0

    while (attempts < maxAttempts) {
      try {
        const analysis = await this.getFilingAnalysis(accessionNumber)
        return analysis
      } catch (error) {
        const apiError = error as APIError
        if (apiError.status_code !== 404) {
          throw error
        }

        attempts++
        if (attempts >= maxAttempts) {
          const error: APIError = {
            detail: 'Analysis did not complete within the expected timeframe',
            status_code: 408,
            error_code: 'ANALYSIS_TIMEOUT',
          }
          throw error
        }

        await new Promise((resolve) => setTimeout(resolve, pollIntervalMs))
      }
    }

    const error: APIError = {
      detail: 'Maximum polling attempts exceeded',
      status_code: 408,
      error_code: 'POLLING_TIMEOUT',
    }
    throw error
  }

  // Private helper methods

  /**
   * Validate search parameters
   */
  private validateSearchParams(params: FilingSearchParams): void {
    if (!params.ticker || typeof params.ticker !== 'string') {
      const error: APIError = {
        detail: 'Ticker is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_TICKER',
      }
      throw error
    }

    // Validate ticker format (basic check)
    const tickerRegex = /^[A-Z0-9.-]+$/i
    if (!tickerRegex.test(params.ticker)) {
      const error: APIError = {
        detail:
          'Invalid ticker format. Must contain only alphanumeric characters, dots, and hyphens',
        status_code: 400,
        error_code: 'INVALID_TICKER_FORMAT',
      }
      throw error
    }

    // Validate date formats if provided
    if (params.start_date && !/^\d{4}-\d{2}-\d{2}$/.test(params.start_date)) {
      const error: APIError = {
        detail: 'Invalid start_date format. Expected format: YYYY-MM-DD',
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      }
      throw error
    }

    if (params.end_date && !/^\d{4}-\d{2}-\d{2}$/.test(params.end_date)) {
      const error: APIError = {
        detail: 'Invalid end_date format. Expected format: YYYY-MM-DD',
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      }
      throw error
    }

    // Validate pagination parameters
    if (params.page !== undefined && (params.page < 1 || !Number.isInteger(params.page))) {
      const error: APIError = {
        detail: 'Page must be a positive integer',
        status_code: 400,
        error_code: 'INVALID_PAGE',
      }
      throw error
    }

    if (
      params.page_size !== undefined &&
      (params.page_size < 1 || params.page_size > 100 || !Number.isInteger(params.page_size))
    ) {
      const error: APIError = {
        detail: 'Page size must be an integer between 1 and 100',
        status_code: 400,
        error_code: 'INVALID_PAGE_SIZE',
      }
      throw error
    }
  }

  /**
   * Validate Edgar search parameters
   */
  private validateEdgarSearchParams(params: EdgarSearchParams): void {
    if (!params.ticker || typeof params.ticker !== 'string') {
      const error: APIError = {
        detail: 'Ticker is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_TICKER',
      }
      throw error
    }

    // Validate ticker format (basic check)
    const tickerRegex = /^[A-Z0-9.-]+$/i
    if (!tickerRegex.test(params.ticker)) {
      const error: APIError = {
        detail:
          'Invalid ticker format. Must contain only alphanumeric characters, dots, and hyphens',
        status_code: 400,
        error_code: 'INVALID_TICKER_FORMAT',
      }
      throw error
    }

    // Validate date formats if provided
    if (params.date_from && !/^\d{4}-\d{2}-\d{2}$/.test(params.date_from)) {
      const error: APIError = {
        detail: 'Invalid date_from format. Expected format: YYYY-MM-DD',
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      }
      throw error
    }

    if (params.date_to && !/^\d{4}-\d{2}-\d{2}$/.test(params.date_to)) {
      const error: APIError = {
        detail: 'Invalid date_to format. Expected format: YYYY-MM-DD',
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      }
      throw error
    }

    // Validate date range
    if (params.date_from && params.date_to && params.date_from > params.date_to) {
      const error: APIError = {
        detail: 'date_from cannot be later than date_to',
        status_code: 400,
        error_code: 'INVALID_DATE_RANGE',
      }
      throw error
    }

    // Validate pagination parameters
    if (params.page !== undefined && (params.page < 1 || !Number.isInteger(params.page))) {
      const error: APIError = {
        detail: 'Page must be a positive integer',
        status_code: 400,
        error_code: 'INVALID_PAGE',
      }
      throw error
    }

    if (
      params.page_size !== undefined &&
      (params.page_size < 1 || params.page_size > 100 || !Number.isInteger(params.page_size))
    ) {
      const error: APIError = {
        detail: 'Page size must be an integer between 1 and 100',
        status_code: 400,
        error_code: 'INVALID_PAGE_SIZE',
      }
      throw error
    }

    // Validate sort parameters
    if (
      params.sort_by &&
      !['filing_date', 'filing_type', 'company_name'].includes(params.sort_by)
    ) {
      const error: APIError = {
        detail: 'Invalid sort_by field. Must be one of: filing_date, filing_type, company_name',
        status_code: 400,
        error_code: 'INVALID_SORT_FIELD',
      }
      throw error
    }

    if (params.sort_direction && !['asc', 'desc'].includes(params.sort_direction)) {
      const error: APIError = {
        detail: 'Invalid sort_direction. Must be one of: asc, desc',
        status_code: 400,
        error_code: 'INVALID_SORT_DIRECTION',
      }
      throw error
    }
  }

  /**
   * Validate accession number format
   */
  private validateAccessionNumber(accessionNumber: string): void {
    if (!accessionNumber || typeof accessionNumber !== 'string') {
      const error: APIError = {
        detail: 'Accession number is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_ACCESSION_NUMBER',
      }
      throw error
    }

    // Basic format validation for SEC accession numbers
    // Format: XXXXXXXXXX-XX-XXXXXX (10 digits, dash, 2 digits, dash, 6 digits)
    const accessionRegex = /^\d{10}-\d{2}-\d{6}$/
    if (!accessionRegex.test(accessionNumber)) {
      const error: APIError = {
        detail: 'Invalid accession number format. Expected format: XXXXXXXXXX-XX-XXXXXX',
        status_code: 400,
        error_code: 'INVALID_ACCESSION_FORMAT',
      }
      throw error
    }
  }

  /**
   * Validate filing ID (UUID) format
   */
  private validateFilingId(filingId: string): void {
    if (!filingId || typeof filingId !== 'string') {
      const error: APIError = {
        detail: 'Filing ID is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_FILING_ID',
      }
      throw error
    }

    // Basic format validation for UUIDs
    // Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    if (!uuidRegex.test(filingId)) {
      const error: APIError = {
        detail:
          'Invalid filing ID format. Expected UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        status_code: 400,
        error_code: 'INVALID_FILING_ID_FORMAT',
      }
      throw error
    }
  }

  /**
   * Validate analysis options
   */
  private validateAnalysisOptions(options: AnalyzeFilingRequest): void {
    if (options.sections && Array.isArray(options.sections)) {
      if (options.sections.length === 0) {
        const error: APIError = {
          detail: 'Sections array cannot be empty when provided',
          status_code: 400,
          error_code: 'INVALID_SECTIONS',
        }
        throw error
      }

      // Validate section names
      const validSections = [
        'business_analysis',
        'risk_factors',
        'management_discussion',
        'balance_sheet',
        'income_statement',
        'cash_flow',
      ]

      for (const section of options.sections) {
        if (!validSections.includes(section)) {
          const error: APIError = {
            detail: `Invalid section name: ${section}. Valid sections are: ${validSections.join(', ')}`,
            status_code: 400,
            error_code: 'INVALID_SECTION_NAME',
          }
          throw error
        }
      }
    }
  }

  /**
   * Handle and enhance filing-related errors
   */
  private handleFilingError(error: unknown, operation: string, accessionNumber: string): APIError {
    if (error && typeof error === 'object' && 'detail' in error && 'status_code' in error) {
      const apiError = error as APIError
      // Enhance existing API errors with more context
      return {
        detail: `Failed ${operation} ${accessionNumber}: ${apiError.detail}`,
        status_code: apiError.status_code,
        error_code: apiError.error_code,
      }
    }

    // Handle unexpected errors
    return {
      detail: `Unexpected error occurred while ${operation} ${accessionNumber}`,
      status_code: 500,
      error_code: 'FILING_SERVICE_ERROR',
    }
  }
}

// Create a singleton instance
export const filingService = new FilingService()
