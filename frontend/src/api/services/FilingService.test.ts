import { describe, it, expect, vi, beforeEach } from 'vitest'
import { FilingService } from './FilingService'
import { filingsApi } from '../filings'
import type { APIError } from '../types'

// Mock the API
vi.mock('../filings', () => ({
  filingsApi: {
    searchFilings: vi.fn(),
    getFiling: vi.fn(),
    getFilingById: vi.fn(),
    analyzeFiling: vi.fn(),
    getFilingAnalysis: vi.fn(),
  },
}))

const mockApi = filingsApi as any

describe('FilingService', () => {
  let filingService: FilingService

  beforeEach(() => {
    filingService = new FilingService()
    vi.clearAllMocks()
  })

  describe('searchFilings', () => {
    it('should search filings successfully', async () => {
      const mockResponse = {
        items: [
          {
            filing_id: '1',
            accession_number: '0000320193-23-000106',
            company_name: 'Apple Inc.',
            ticker: 'AAPL',
            form_type: '10-K',
            filing_date: '2023-11-03',
            period_of_report: '2023-09-30',
            document_count: 5,
            size_bytes: 1024000,
            filing_url: 'https://example.com/filing',
            created_at: '2023-11-03T10:00:00Z',
            updated_at: '2023-11-03T10:00:00Z',
          },
        ],
        pagination: {
          page: 1,
          page_size: 10,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
          next_page: null,
          previous_page: null,
        },
      }

      mockApi.searchFilings.mockResolvedValue(mockResponse)

      const result = await filingService.searchFilings({ ticker: 'AAPL' })

      expect(mockApi.searchFilings).toHaveBeenCalledWith({ ticker: 'AAPL' })
      expect(result).toEqual(mockResponse)
    })

    it('should validate ticker parameter', async () => {
      await expect(filingService.searchFilings({ ticker: '' })).rejects.toMatchObject({
        detail: 'Ticker is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_TICKER',
      })

      await expect(filingService.searchFilings({ ticker: 'INVALID@TICKER' })).rejects.toMatchObject({
        detail: expect.stringContaining('Invalid ticker format'),
        status_code: 400,
        error_code: 'INVALID_TICKER_FORMAT',
      })
    })

    it('should validate date formats', async () => {
      await expect(
        filingService.searchFilings({ ticker: 'AAPL', start_date: 'invalid-date' })
      ).rejects.toMatchObject({
        detail: expect.stringContaining('Invalid start_date format'),
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      })

      await expect(
        filingService.searchFilings({ ticker: 'AAPL', end_date: '2023/01/01' })
      ).rejects.toMatchObject({
        detail: expect.stringContaining('Invalid end_date format'),
        status_code: 400,
        error_code: 'INVALID_DATE_FORMAT',
      })
    })

    it('should validate pagination parameters', async () => {
      await expect(filingService.searchFilings({ ticker: 'AAPL', page: 0 })).rejects.toMatchObject({
        detail: 'Page must be a positive integer',
        status_code: 400,
        error_code: 'INVALID_PAGE',
      })

      await expect(
        filingService.searchFilings({ ticker: 'AAPL', page_size: 101 })
      ).rejects.toMatchObject({
        detail: 'Page size must be an integer between 1 and 100',
        status_code: 400,
        error_code: 'INVALID_PAGE_SIZE',
      })
    })

    it('should handle API errors gracefully', async () => {
      const apiError: APIError = {
        detail: 'Company not found',
        status_code: 404,
        error_code: 'COMPANY_NOT_FOUND',
      }

      mockApi.searchFilings.mockRejectedValue(apiError)

      await expect(filingService.searchFilings({ ticker: 'NOTFOUND' })).rejects.toMatchObject({
        detail: 'Failed searching filings for ticker NOTFOUND: Company not found',
        status_code: 404,
        error_code: 'COMPANY_NOT_FOUND',
      })
    })

    it('should handle unexpected errors', async () => {
      mockApi.searchFilings.mockRejectedValue(new Error('Network error'))

      await expect(filingService.searchFilings({ ticker: 'AAPL' })).rejects.toMatchObject({
        detail: 'Unexpected error occurred while searching filings for ticker AAPL',
        status_code: 500,
        error_code: 'FILING_SERVICE_ERROR',
      })
    })
  })

  describe('getFiling', () => {
    it('should get filing by accession number successfully', async () => {
      const mockFiling = {
        filing_id: '1',
        accession_number: '0000320193-23-000106',
        company_name: 'Apple Inc.',
        ticker: 'AAPL',
        form_type: '10-K',
        filing_date: '2023-11-03',
        period_of_report: '2023-09-30',
        document_count: 5,
        size_bytes: 1024000,
        filing_url: 'https://example.com/filing',
        created_at: '2023-11-03T10:00:00Z',
        updated_at: '2023-11-03T10:00:00Z',
      }

      mockApi.getFiling.mockResolvedValue(mockFiling)

      const result = await filingService.getFiling('0000320193-23-000106')

      expect(mockApi.getFiling).toHaveBeenCalledWith('0000320193-23-000106')
      expect(result).toEqual(mockFiling)
    })

    it('should validate accession number format', async () => {
      await expect(filingService.getFiling('')).rejects.toMatchObject({
        detail: 'Accession number is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_ACCESSION_NUMBER',
      })

      await expect(filingService.getFiling('invalid-format')).rejects.toMatchObject({
        detail: expect.stringContaining('Invalid accession number format'),
        status_code: 400,
        error_code: 'INVALID_ACCESSION_FORMAT',
      })
    })
  })

  describe('getFilingById', () => {
    it('should get filing by UUID successfully', async () => {
      const mockFiling = {
        filing_id: '12345678-1234-1234-1234-123456789abc',
        accession_number: '0000320193-23-000106',
        company_name: 'Apple Inc.',
        ticker: 'AAPL',
        form_type: '10-K',
        filing_date: '2023-11-03',
        period_of_report: '2023-09-30',
        document_count: 5,
        size_bytes: 1024000,
        filing_url: 'https://example.com/filing',
        created_at: '2023-11-03T10:00:00Z',
        updated_at: '2023-11-03T10:00:00Z',
      }

      mockApi.getFilingById.mockResolvedValue(mockFiling)

      const result = await filingService.getFilingById('12345678-1234-1234-1234-123456789abc')

      expect(mockApi.getFilingById).toHaveBeenCalledWith('12345678-1234-1234-1234-123456789abc')
      expect(result).toEqual(mockFiling)
    })

    it('should validate filing ID format', async () => {
      await expect(filingService.getFilingById('')).rejects.toMatchObject({
        detail: 'Filing ID is required and must be a string',
        status_code: 400,
        error_code: 'INVALID_FILING_ID',
      })

      await expect(filingService.getFilingById('invalid-uuid')).rejects.toMatchObject({
        detail: expect.stringContaining('Invalid filing ID format'),
        status_code: 400,
        error_code: 'INVALID_FILING_ID_FORMAT',
      })
    })
  })

  describe('analyzeFiling', () => {
    it('should analyze filing successfully', async () => {
      const mockTask = {
        task_id: 'task-123',
        status: 'pending' as const,
        created_at: '2023-11-03T10:00:00Z',
      }

      mockApi.analyzeFiling.mockResolvedValue(mockTask)

      const result = await filingService.analyzeFiling('0000320193-23-000106')

      expect(mockApi.analyzeFiling).toHaveBeenCalledWith('0000320193-23-000106', undefined)
      expect(result).toEqual(mockTask)
    })

    it('should validate analysis options', async () => {
      await expect(
        filingService.analyzeFiling('0000320193-23-000106', { sections: [] })
      ).rejects.toMatchObject({
        detail: 'Sections array cannot be empty when provided',
        status_code: 400,
        error_code: 'INVALID_SECTIONS',
      })
    })
  })

  describe('getFilingAnalysis', () => {
    it('should get filing analysis successfully', async () => {
      const mockAnalysis = {
        analysis_id: '1',
        filing_id: 'filing-123',
        accession_number: '0000320193-23-000106',
        filing_summary: 'Test summary',
        executive_summary: 'Test executive summary',
        key_insights: ['Insight 1'],
        financial_highlights: ['Highlight 1'],
        risk_factors: ['Risk 1'],
        opportunities: ['Opportunity 1'],
        confidence_score: 0.95,
        sections_analyzed: 5,
        processing_time_seconds: 120,
        created_at: '2023-11-03T10:00:00Z',
        updated_at: '2023-11-03T10:00:00Z',
        full_results: {
          sections: [
            {
              section_name: 'Business Overview',
              summary: 'Section summary',
            },
          ],
        },
      }

      mockApi.getFilingAnalysis.mockResolvedValue(mockAnalysis)

      const result = await filingService.getFilingAnalysis('0000320193-23-000106')

      expect(mockApi.getFilingAnalysis).toHaveBeenCalledWith('0000320193-23-000106')
      expect(result).toEqual(mockAnalysis)
    })
  })

  describe('hasAnalysis', () => {
    it('should return true when analysis exists', async () => {
      const mockAnalysis = { analysis_id: '1' }
      mockApi.getFilingAnalysis.mockResolvedValue(mockAnalysis)

      const result = await filingService.hasAnalysis('0000320193-23-000106')

      expect(result).toBe(true)
    })

    it('should return false when analysis does not exist', async () => {
      const apiError: APIError = {
        detail: 'Analysis not found',
        status_code: 404,
        error_code: 'ANALYSIS_NOT_FOUND',
      }

      mockApi.getFilingAnalysis.mockRejectedValue(apiError)

      const result = await filingService.hasAnalysis('0000320193-23-000106')

      expect(result).toBe(false)
    })

    it('should re-throw non-404 errors', async () => {
      const apiError: APIError = {
        detail: 'Server error',
        status_code: 500,
        error_code: 'SERVER_ERROR',
      }

      mockApi.getFilingAnalysis.mockRejectedValue(apiError)

      await expect(filingService.hasAnalysis('0000320193-23-000106')).rejects.toMatchObject({
        detail: expect.stringContaining('Server error'),
        status_code: 500,
        error_code: 'SERVER_ERROR',
      })
    })
  })
})
