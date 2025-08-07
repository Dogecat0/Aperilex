import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCompany, useCompanyAnalyses, useCompanyFilings } from './useCompany'
import { aperilexApi } from '@/api'
import type { CompanyResponse, AnalysisResponse, FilingResponse } from '@/api/types'
import React, { ReactNode } from 'react'

// Mock the API
vi.mock('@/api', () => ({
  aperilexApi: {
    companies: {
      getCompany: vi.fn(),
      getCompanyAnalyses: vi.fn(),
      getCompanyFilings: vi.fn(),
    },
  },
}))

const mockApi = aperilexApi.companies as any

describe('useCompany hooks', () => {
  let queryClient: QueryClient

  const createWrapper = ({ children }: { children: ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  describe('useCompany', () => {
    it('should fetch company data successfully', async () => {
      const ticker = 'AAPL'
      const mockCompany: CompanyResponse = {
        company_id: '320193',
        ticker: 'AAPL',
        name: 'Apple Inc.',
        display_name: 'Apple Inc.',
        cik: '0000320193',
        sic_code: '3571',
        sic_description: 'Electronic Computers',
        industry: 'Technology',
        fiscal_year_end: '09-30',
        business_address: {
          street: '1 Apple Park Way',
          city: 'Cupertino',
          state: 'CA',
          zipcode: '95014',
          country: 'US',
        },
      }

      mockApi.getCompany.mockResolvedValue(mockCompany)

      const { result } = renderHook(() => useCompany(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompany).toHaveBeenCalledWith(ticker, false)
      expect(result.current.data).toEqual(mockCompany)
    })

    it('should include recent analyses when requested', async () => {
      const ticker = 'AAPL'
      const mockCompany: CompanyResponse = {
        company_id: '320193',
        ticker: 'AAPL',
        name: 'Apple Inc.',
        display_name: 'Apple Inc.',
        cik: '0000320193',
        sic_code: '3571',
        sic_description: 'Electronic Computers',
        industry: 'Technology',
        fiscal_year_end: '09-30',
        business_address: {
          street: '1 Apple Park Way',
          city: 'Cupertino',
          state: 'CA',
          zipcode: '95014',
          country: 'US',
        },
        recent_analyses: [
          {
            analysis_id: 'analysis-123',
            analysis_type: 'COMPREHENSIVE',
            created_at: '2024-01-15T10:00:00Z',
            confidence_score: 0.95,
          },
        ],
      }

      mockApi.getCompany.mockResolvedValue(mockCompany)

      const { result } = renderHook(
        () => useCompany(ticker, { includeRecentAnalyses: true }),
        { wrapper: createWrapper }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompany).toHaveBeenCalledWith(ticker, true)
      expect(result.current.data).toEqual(mockCompany)
      expect(result.current.data?.recent_analyses).toBeDefined()
      expect(result.current.data?.recent_analyses).toHaveLength(1)
    })

    it('should not fetch when ticker is empty', () => {
      mockApi.getCompany.mockResolvedValue({})

      renderHook(() => useCompany(''), { wrapper: createWrapper })

      expect(mockApi.getCompany).not.toHaveBeenCalled()
    })

    it('should not fetch when enabled is false', () => {
      const ticker = 'AAPL'
      mockApi.getCompany.mockResolvedValue({})

      renderHook(() => useCompany(ticker, { enabled: false }), { wrapper: createWrapper })

      expect(mockApi.getCompany).not.toHaveBeenCalled()
    })

    it('should handle API errors gracefully', async () => {
      const ticker = 'INVALID'
      const error = new Error('Company not found')
      mockApi.getCompany.mockRejectedValue(error)

      const { result } = renderHook(() => useCompany(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })

    it('should show loading state initially', () => {
      const ticker = 'AAPL'
      mockApi.getCompany.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useCompany(ticker), { wrapper: createWrapper })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should use correct query key for caching', () => {
      const ticker = 'AAPL'
      const includeRecentAnalyses = true
      mockApi.getCompany.mockResolvedValue({})

      renderHook(
        () => useCompany(ticker, { includeRecentAnalyses }),
        { wrapper: createWrapper }
      )

      // The query key should include the includeRecentAnalyses option for proper caching
      const queryState = queryClient.getQueryState(['company', ticker, { includeRecentAnalyses }])
      expect(queryState).toBeDefined()
    })
  })

  describe('useCompanyAnalyses', () => {
    it('should fetch company analyses successfully', async () => {
      const ticker = 'AAPL'
      const mockAnalyses: AnalysisResponse[] = [
        {
          analysis_id: '1',
          filing_id: 'filing1',
          analysis_type: 'COMPREHENSIVE',
          created_by: 'system',
          created_at: '2024-01-01T00:00:00Z',
          confidence_score: 0.95,
          llm_provider: 'openai',
          llm_model: 'gpt-4',
          processing_time_seconds: 45,
          filing_summary: 'Test summary',
          executive_summary: 'Test executive summary',
          key_insights: ['Insight 1'],
          risk_factors: ['Risk 1'],
          opportunities: ['Opportunity 1'],
          financial_highlights: ['Highlight 1'],
          sections_analyzed: 3,
        },
      ]

      mockApi.getCompanyAnalyses.mockResolvedValue(mockAnalyses)

      const { result } = renderHook(() => useCompanyAnalyses(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompanyAnalyses).toHaveBeenCalledWith(ticker, {})
      expect(result.current.data).toEqual(mockAnalyses)
    })

    it('should pass filters correctly', async () => {
      const ticker = 'AAPL'
      const filters = {
        page: 1,
        page_size: 10,
        analysis_type: 'FINANCIAL_FOCUSED' as const,
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      }

      mockApi.getCompanyAnalyses.mockResolvedValue([])

      const { result } = renderHook(
        () => useCompanyAnalyses(ticker, filters),
        { wrapper: createWrapper }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompanyAnalyses).toHaveBeenCalledWith(ticker, filters)
    })

    it('should not fetch when ticker is empty', () => {
      mockApi.getCompanyAnalyses.mockResolvedValue([])

      renderHook(() => useCompanyAnalyses(''), { wrapper: createWrapper })

      expect(mockApi.getCompanyAnalyses).not.toHaveBeenCalled()
    })

    it('should not fetch when enabled is false', () => {
      const ticker = 'AAPL'
      mockApi.getCompanyAnalyses.mockResolvedValue([])

      renderHook(
        () => useCompanyAnalyses(ticker, { enabled: false }),
        { wrapper: createWrapper }
      )

      expect(mockApi.getCompanyAnalyses).not.toHaveBeenCalled()
    })

    it('should handle empty results', async () => {
      const ticker = 'AAPL'
      mockApi.getCompanyAnalyses.mockResolvedValue([])

      const { result } = renderHook(() => useCompanyAnalyses(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual([])
    })

    it('should handle API errors', async () => {
      const ticker = 'AAPL'
      const error = new Error('Failed to fetch analyses')
      mockApi.getCompanyAnalyses.mockRejectedValue(error)

      const { result } = renderHook(() => useCompanyAnalyses(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })

    it('should use correct query key with filters for caching', () => {
      const ticker = 'AAPL'
      const filters = { analysis_type: 'COMPREHENSIVE' as const, page: 1 }
      mockApi.getCompanyAnalyses.mockResolvedValue([])

      renderHook(() => useCompanyAnalyses(ticker, filters), { wrapper: createWrapper })

      const queryState = queryClient.getQueryState(['company', ticker, 'analyses', filters])
      expect(queryState).toBeDefined()
    })
  })

  describe('useCompanyFilings', () => {
    it('should fetch company filings successfully', async () => {
      const ticker = 'AAPL'
      const mockFilings: FilingResponse[] = [
        {
          filing_id: '1',
          company_id: '320193',
          accession_number: '0000320193-24-000001',
          filing_type: '10-K',
          filing_date: '2024-01-15',
          processing_status: 'completed',
          processing_error: null,
          metadata: {
            period_end_date: '2023-12-31',
            sec_url: 'https://sec.gov/filing/123',
          },
          analyses_count: 2,
          latest_analysis_date: '2024-01-16T10:00:00Z',
        },
      ]

      mockApi.getCompanyFilings.mockResolvedValue(mockFilings)

      const { result } = renderHook(() => useCompanyFilings(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompanyFilings).toHaveBeenCalledWith(ticker, {})
      expect(result.current.data).toEqual(mockFilings)
    })

    it('should pass filing filters correctly', async () => {
      const ticker = 'AAPL'
      const filters = {
        page: 1,
        page_size: 20,
        filing_type: '10-K',
        date_from: '2024-01-01',
        date_to: '2024-12-31',
        has_analysis: true,
      }

      mockApi.getCompanyFilings.mockResolvedValue([])

      const { result } = renderHook(
        () => useCompanyFilings(ticker, filters),
        { wrapper: createWrapper }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getCompanyFilings).toHaveBeenCalledWith(ticker, filters)
    })

    it('should not fetch when ticker is empty', () => {
      mockApi.getCompanyFilings.mockResolvedValue([])

      renderHook(() => useCompanyFilings(''), { wrapper: createWrapper })

      expect(mockApi.getCompanyFilings).not.toHaveBeenCalled()
    })

    it('should not fetch when enabled is false', () => {
      const ticker = 'AAPL'
      mockApi.getCompanyFilings.mockResolvedValue([])

      renderHook(
        () => useCompanyFilings(ticker, { enabled: false }),
        { wrapper: createWrapper }
      )

      expect(mockApi.getCompanyFilings).not.toHaveBeenCalled()
    })

    it('should handle empty results', async () => {
      const ticker = 'NEWCOMPANY'
      mockApi.getCompanyFilings.mockResolvedValue([])

      const { result } = renderHook(() => useCompanyFilings(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual([])
    })

    it('should handle API errors', async () => {
      const ticker = 'INVALID'
      const error = new Error('Company not found')
      mockApi.getCompanyFilings.mockRejectedValue(error)

      const { result } = renderHook(() => useCompanyFilings(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })

    it('should show loading state', () => {
      const ticker = 'AAPL'
      mockApi.getCompanyFilings.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useCompanyFilings(ticker), { wrapper: createWrapper })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })

    it('should handle paginated results', async () => {
      const ticker = 'AAPL'
      const paginatedResponse = {
        items: [
          {
            filing_id: '1',
            company_id: '320193',
            accession_number: '0000320193-24-000001',
            filing_type: '10-K',
            filing_date: '2024-01-15',
            processing_status: 'completed' as const,
            processing_error: null,
            metadata: {},
          },
        ],
        pagination: {
          page: 1,
          page_size: 20,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
          next_page: null,
          previous_page: null,
        },
      }

      mockApi.getCompanyFilings.mockResolvedValue(paginatedResponse)

      const { result } = renderHook(() => useCompanyFilings(ticker), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toEqual(paginatedResponse)
    })

    it('should use correct query key with filters for caching', () => {
      const ticker = 'AAPL'
      const filters = { filing_type: '10-K', page: 1 }
      mockApi.getCompanyFilings.mockResolvedValue([])

      renderHook(() => useCompanyFilings(ticker, filters), { wrapper: createWrapper })

      const queryState = queryClient.getQueryState(['company', ticker, 'filings', filters])
      expect(queryState).toBeDefined()
    })
  })
})