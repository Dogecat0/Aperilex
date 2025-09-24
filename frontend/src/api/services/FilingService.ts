import { filingsApi, type FilingSearchParams } from '../filings'
import type {
  FilingResponse,
  AnalysisResponse,
  TaskResponse,
  AnalyzeFilingRequest,
  ComprehensiveAnalysisResponse,
  PaginatedResponse,
  APIError,
} from '../types'

/**
 * Service class for Filing-related operations using filing UUIDs.
 */
export class FilingService {
  /**
   * Search filings by ticker with optional filters (database search).
   */
  async searchFilings(
    params: FilingSearchParams
  ): Promise<PaginatedResponse<FilingResponse>> {
    this.validateSearchParams(params)

    try {
      return await filingsApi.searchFilings(params)
    } catch (error) {
      throw this.handleFilingError(error, 'searching filings for ticker', params.ticker)
    }
  }

  /**
   * Retrieve filing information by filing UUID.
   */
  async getFilingById(filingId: string): Promise<FilingResponse> {
    this.validateFilingId(filingId)

    try {
      return await filingsApi.getFilingById(filingId)
    } catch (error) {
      throw this.handleFilingError(error, 'retrieving filing', filingId)
    }
  }

  /**
   * Initiate analysis of a filing identified by its UUID.
   */
  async analyzeFiling(
    filingId: string,
    options?: AnalyzeFilingRequest
  ): Promise<TaskResponse> {
    this.validateFilingId(filingId)

    if (options) {
      this.validateAnalysisOptions(options)
    }

    try {
      return await filingsApi.analyzeFiling(filingId, options)
    } catch (error) {
      throw this.handleFilingError(error, 'initiating analysis for filing', filingId)
    }
  }

  /**
   * Retrieve the latest analysis for a filing by UUID.
   */
  async getFilingAnalysisById(filingId: string): Promise<AnalysisResponse> {
    this.validateFilingId(filingId)

    try {
      return await filingsApi.getFilingAnalysisById(filingId)
    } catch (error) {
      throw this.handleFilingError(error, 'retrieving analysis for filing', filingId)
    }
  }

  /**
   * Retrieve comprehensive analysis results for a filing.
   */
  async getComprehensiveAnalysis(
    filingId: string
  ): Promise<ComprehensiveAnalysisResponse> {
    const analysis = await this.getFilingAnalysisById(filingId)

    if (!analysis.full_results) {
      const error: APIError = {
        detail: 'Comprehensive analysis results not available for this filing',
        status_code: 404,
        error_code: 'ANALYSIS_INCOMPLETE',
      }
      throw error
    }

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
          overall_sentiment: 0,
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
      filing_type: '',
      company_name: '',
      analysis_timestamp: analysis.created_at,
    }
  }

  /**
   * Determine whether a filing already has analysis results.
   */
  async hasAnalysis(filingId: string): Promise<boolean> {
    try {
      await this.getFilingAnalysisById(filingId)
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
   * Retrieve filing metadata and analysis availability in a single call.
   */
  async getFilingStatus(
    filingId: string
  ): Promise<
    FilingResponse & {
      has_analysis: boolean
      analysis_date?: string
    }
  > {
    const filing = await this.getFilingById(filingId)
    const hasAnalysis = await this.hasAnalysis(filingId)

    let analysisDate: string | undefined
    if (hasAnalysis) {
      try {
        const analysis = await this.getFilingAnalysisById(filingId)
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
   * Poll until an analysis result becomes available for the given filing.
   */
  async pollForAnalysisCompletion(
    filingId: string,
    pollIntervalMs: number = 5000,
    maxAttempts: number = 24
  ): Promise<AnalysisResponse> {
    let attempts = 0

    while (attempts < maxAttempts) {
      try {
        return await this.getFilingAnalysisById(filingId)
      } catch (error) {
        const apiError = error as APIError
        if (apiError.status_code !== 404) {
          throw error
        }

        attempts += 1
        if (attempts >= maxAttempts) {
          const timeoutError: APIError = {
            detail: 'Analysis did not complete within the expected timeframe',
            status_code: 408,
            error_code: 'ANALYSIS_TIMEOUT',
          }
          throw timeoutError
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

  private validateSearchParams(params: FilingSearchParams): void {
    if (!params.ticker || typeof params.ticker !== 'string') {
      const error: APIError = {
        detail: 'Ticker is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_TICKER',
      }
      throw error
    }

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

  private validateFilingId(filingId: string): void {
    if (!filingId || typeof filingId !== 'string') {
      const error: APIError = {
        detail: 'Filing ID is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_FILING_ID',
      }
      throw error
    }

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

  private handleFilingError(
    error: unknown,
    operation: string,
    identifier: string
  ): APIError {
    if (error && typeof error === 'object' && 'detail' in error && 'status_code' in error) {
      const apiError = error as APIError
      return {
        detail: `Failed ${operation} ${identifier}: ${apiError.detail}`,
        status_code: apiError.status_code,
        error_code: apiError.error_code,
      }
    }

    return {
      detail: `Unexpected error occurred while ${operation} ${identifier}`,
      status_code: 500,
      error_code: 'FILING_SERVICE_ERROR',
    }
  }
}

export const filingService = new FilingService()
