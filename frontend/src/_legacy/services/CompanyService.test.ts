import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CompanyService } from './CompanyService'
import { aperilexApi } from '@/api'

// Mock the API
vi.mock('@/api', () => ({
  aperilexApi: {
    companies: {
      getCompany: vi.fn(),
      getCompanyAnalyses: vi.fn(),
    },
  },
}))

const mockApi = aperilexApi.companies as any

describe('CompanyService', () => {
  let companyService: CompanyService

  beforeEach(() => {
    companyService = new CompanyService()
    vi.clearAllMocks()
  })

  describe('getCompany', () => {
    it('should fetch company data successfully', async () => {
      const mockCompany = {
        company_id: '1',
        cik: '0000320193',
        name: 'Apple Inc.',
        ticker: 'AAPL',
        display_name: 'Apple Inc.',
        industry: 'Technology',
        sic_code: '3571',
        sic_description: 'Electronic Computers',
        fiscal_year_end: '09-30',
        business_address: {
          street: '1 Apple Park Way',
          city: 'Cupertino',
          state: 'CA',
          zipcode: '95014',
          country: 'USA',
        },
      }

      mockApi.getCompany.mockResolvedValue(mockCompany)

      const result = await companyService.getCompany('AAPL')

      expect(mockApi.getCompany).toHaveBeenCalledWith('AAPL', undefined)
      expect(result).toEqual(mockCompany)
    })

    it('should normalize ticker to uppercase', async () => {
      const mockCompany = { company_id: '1', ticker: 'AAPL' }
      mockApi.getCompany.mockResolvedValue(mockCompany)

      await companyService.getCompany('aapl')

      expect(mockApi.getCompany).toHaveBeenCalledWith('AAPL', undefined)
    })

    it('should include recent analyses when requested', async () => {
      const mockCompany = { company_id: '1', ticker: 'AAPL' }
      mockApi.getCompany.mockResolvedValue(mockCompany)

      await companyService.getCompany('AAPL', { includeRecentAnalyses: true })

      expect(mockApi.getCompany).toHaveBeenCalledWith('AAPL', true)
    })

    it('should throw error for invalid ticker', async () => {
      await expect(companyService.getCompany('')).rejects.toThrow(
        'Ticker symbol is required and must be a string'
      )

      await expect(companyService.getCompany('TOOLONGTICKER123')).rejects.toThrow(
        'Ticker symbol must be between 1 and 10 characters'
      )
    })

    it('should handle API errors gracefully', async () => {
      mockApi.getCompany.mockRejectedValue(new Error('Network error'))

      await expect(companyService.getCompany('AAPL')).rejects.toThrow(
        'Failed to fetch company data for AAPL: Network error'
      )
    })
  })

  describe('getCompanyAnalyses', () => {
    it('should fetch company analyses successfully', async () => {
      const mockAnalyses = [
        {
          analysis_id: '1',
          filing_id: 'filing1',
          analysis_template: 'comprehensive' as const,
          created_by: 'system',
          created_at: '2023-01-01T00:00:00Z',
          confidence_score: 0.95,
          llm_provider: 'openai',
          llm_model: 'gpt-4',
          processing_time_seconds: 45,
        },
      ]

      mockApi.getCompanyAnalyses.mockResolvedValue(mockAnalyses)

      const result = await companyService.getCompanyAnalyses('AAPL')

      expect(mockApi.getCompanyAnalyses).toHaveBeenCalledWith('AAPL', {})
      expect(result).toEqual(mockAnalyses)
    })

    it('should validate date formats', async () => {
      await expect(
        companyService.getCompanyAnalyses('AAPL', { start_date: 'invalid-date' })
      ).rejects.toThrow('start_date must be in YYYY-MM-DD format')

      await expect(
        companyService.getCompanyAnalyses('AAPL', { end_date: '2023/01/01' })
      ).rejects.toThrow('end_date must be in YYYY-MM-DD format')
    })

    it('should validate date range', async () => {
      await expect(
        companyService.getCompanyAnalyses('AAPL', {
          start_date: '2023-12-31',
          end_date: '2023-01-01',
        })
      ).rejects.toThrow('start_date must be before or equal to end_date')
    })

    it('should validate pagination parameters', async () => {
      await expect(companyService.getCompanyAnalyses('AAPL', { page: 0 })).rejects.toThrow(
        'page must be a positive integer'
      )

      await expect(companyService.getCompanyAnalyses('AAPL', { page_size: 101 })).rejects.toThrow(
        'page_size must be a positive integer between 1 and 100'
      )
    })
  })

  describe('getMostRecentAnalysis', () => {
    it('should return most recent analysis for array response', async () => {
      const mockAnalyses = [
        {
          analysis_id: '1',
          filing_id: 'filing1',
          analysis_template: 'comprehensive' as const,
          created_by: 'system',
          created_at: '2023-01-01T00:00:00Z',
          confidence_score: 0.95,
          llm_provider: 'openai',
          llm_model: 'gpt-4',
          processing_time_seconds: 45,
        },
      ]

      mockApi.getCompanyAnalyses.mockResolvedValue(mockAnalyses)

      const result = await companyService.getMostRecentAnalysis('AAPL')

      expect(result).toEqual(mockAnalyses[0])
    })

    it('should return most recent analysis for paginated response', async () => {
      const mockPaginatedResponse = {
        items: [
          {
            analysis_id: '1',
            filing_id: 'filing1',
            analysis_template: 'comprehensive' as const,
            created_by: 'system',
            created_at: '2023-01-01T00:00:00Z',
            confidence_score: 0.95,
            llm_provider: 'openai',
            llm_model: 'gpt-4',
            processing_time_seconds: 45,
          },
        ],
        pagination: {
          page: 1,
          page_size: 1,
          total_items: 5,
          total_pages: 5,
          has_next: true,
          has_previous: false,
          next_page: 2,
          previous_page: null,
        },
      }

      mockApi.getCompanyAnalyses.mockResolvedValue(mockPaginatedResponse)

      const result = await companyService.getMostRecentAnalysis('AAPL')

      expect(result).toEqual(mockPaginatedResponse.items[0])
    })

    it('should return null when no analyses found', async () => {
      mockApi.getCompanyAnalyses.mockResolvedValue([])

      const result = await companyService.getMostRecentAnalysis('AAPL')

      expect(result).toBeNull()
    })
  })

  describe('companyExists', () => {
    it('should return true when company exists', async () => {
      const mockCompany = { company_id: '1', ticker: 'AAPL' }
      mockApi.getCompany.mockResolvedValue(mockCompany)

      const result = await companyService.companyExists('AAPL')

      expect(result).toBe(true)
    })

    it('should return false when company does not exist', async () => {
      mockApi.getCompany.mockRejectedValue(new Error('404'))

      const result = await companyService.companyExists('NOTFOUND')

      expect(result).toBe(false)
    })
  })
})
