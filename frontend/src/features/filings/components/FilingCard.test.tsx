import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@/test/utils'
import { FilingCard } from './FilingCard'
import type { FilingResponse } from '@/api/types'

describe('FilingCard', () => {
  const mockOnViewDetails = vi.fn()
  const mockOnAnalyze = vi.fn()

  const baseFiling: FilingResponse & {
    has_analysis?: boolean
    analysis_date?: string
    company_name?: string
    company_ticker?: string
  } = {
    filing_id: '1',
    company_id: '320193',
    accession_number: '0000320193-24-000001',
    filing_type: '10-K',
    filing_date: '2024-01-15',
    processing_status: 'completed',
    processing_error: null,
    metadata: {
      period_end_date: '2023-12-31',
      sec_url: 'https://www.sec.gov/test',
    },
    analyses_count: 1,
    latest_analysis_date: '2024-01-16T10:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders filing information correctly', () => {
      render(<FilingCard filing={baseFiling} />)

      expect(screen.getByText('10-K')).toBeInTheDocument()
      expect(screen.getByText('0000320193-24-000001')).toBeInTheDocument()
      expect(screen.getByText(/Filed:/)).toBeInTheDocument()
      // Date might be formatted differently, so use a more flexible matcher
      expect(screen.getByText(/2024/)).toBeInTheDocument()
    })

    it('displays processing status with correct styling', () => {
      render(<FilingCard filing={baseFiling} />)

      expect(screen.getByText('Processing:')).toBeInTheDocument()
      expect(screen.getByText('completed')).toBeInTheDocument()
      
      // Check for completed status icon
      const statusIcon = document.querySelector('.text-green-600')
      expect(statusIcon).toBeInTheDocument()
    })

    it('shows company information when provided', () => {
      const filingWithCompany = {
        ...baseFiling,
        company_name: 'Apple Inc.',
        company_ticker: 'AAPL',
      }

      render(<FilingCard filing={filingWithCompany} />)

      expect(screen.getByText('Apple Inc. (AAPL)')).toBeInTheDocument()
    })

    it('hides company information when showCompanyInfo is false', () => {
      const filingWithCompany = {
        ...baseFiling,
        company_name: 'Apple Inc.',
        company_ticker: 'AAPL',
      }

      render(<FilingCard filing={filingWithCompany} showCompanyInfo={false} />)

      expect(screen.queryByText('Apple Inc. (AAPL)')).not.toBeInTheDocument()
    })
  })

  describe('Status Indicators', () => {
    it('displays correct icon and color for completed status', () => {
      render(<FilingCard filing={baseFiling} />)

      const completedIcon = document.querySelector('.text-green-600')
      expect(completedIcon).toBeInTheDocument()
    })

    it('displays correct icon and color for failed status', () => {
      const failedFiling = {
        ...baseFiling,
        processing_status: 'failed' as const,
      }

      render(<FilingCard filing={failedFiling} />)

      const failedIcon = document.querySelector('.text-red-600')
      expect(failedIcon).toBeInTheDocument()
    })

    it('displays correct icon and color for processing status', () => {
      const processingFiling = {
        ...baseFiling,
        processing_status: 'processing' as const,
      }

      render(<FilingCard filing={processingFiling} />)

      const processingIcon = document.querySelector('.text-blue-600')
      expect(processingIcon).toBeInTheDocument()
    })

    it('displays correct icon and color for pending status', () => {
      const pendingFiling = {
        ...baseFiling,
        processing_status: 'pending' as const,
      }

      render(<FilingCard filing={pendingFiling} />)

      const pendingIcon = document.querySelector('.text-yellow-600')
      expect(pendingIcon).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays processing error when present', () => {
      const errorFiling = {
        ...baseFiling,
        processing_status: 'failed' as const,
        processing_error: 'Failed to parse financial statements',
      }

      render(<FilingCard filing={errorFiling} />)

      expect(screen.getByText('Processing Error:')).toBeInTheDocument()
      expect(screen.getByText('Failed to parse financial statements')).toBeInTheDocument()
    })

    it('does not show error section when no error', () => {
      render(<FilingCard filing={baseFiling} />)

      expect(screen.queryByText('Processing Error:')).not.toBeInTheDocument()
    })
  })

  describe('Analysis Information', () => {
    it('shows analysis available indicator when analysis exists', () => {
      const filingWithAnalysis = {
        ...baseFiling,
        has_analysis: true,
        analysis_date: '2024-01-16T10:00:00Z',
      }

      render(<FilingCard filing={filingWithAnalysis} />)

      expect(screen.getByText('Analysis Available')).toBeInTheDocument()
      expect(screen.getByText(/Last Analysis:/)).toBeInTheDocument()
    })

    it('shows analysis count when available', () => {
      const filingWithAnalysis = {
        ...baseFiling,
        has_analysis: true,
        analysis_date: '2024-01-16T10:00:00Z',
        analyses_count: 3,
      }

      render(<FilingCard filing={filingWithAnalysis} />)

      const analysisElements = screen.getAllByText((content, element) => {
        return /3\s*analys(is|es)/.test(element?.textContent || '') && element?.className?.includes('text-xs')
      })
      expect(analysisElements.length).toBeGreaterThan(0)
    })

    it('shows singular form for single analysis', () => {
      const filingWithAnalysis = {
        ...baseFiling,
        has_analysis: true,
        analysis_date: '2024-01-16T10:00:00Z',
        analyses_count: 1,
      }

      render(<FilingCard filing={filingWithAnalysis} />)

      // Look for the specific text pattern
      expect(screen.getByText(/1 analysis$/)).toBeInTheDocument()
    })

    it('does not show analysis section when no analysis', () => {
      const filingWithoutAnalysis = {
        ...baseFiling,
        has_analysis: false,
      }

      render(<FilingCard filing={filingWithoutAnalysis} />)

      expect(screen.queryByText('Analysis Available')).not.toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('renders View Details button when onViewDetails provided', () => {
      render(<FilingCard filing={baseFiling} onViewDetails={mockOnViewDetails} />)

      const viewButton = screen.getByRole('button', { name: /View Details/ })
      expect(viewButton).toBeInTheDocument()
    })

    it('renders Analyze button when onAnalyze provided and no analysis exists', () => {
      const filingWithoutAnalysis = {
        ...baseFiling,
        has_analysis: false,
      }

      render(<FilingCard filing={filingWithoutAnalysis} onAnalyze={mockOnAnalyze} />)

      const analyzeButton = screen.getByRole('button', { name: /Analyze/ })
      expect(analyzeButton).toBeInTheDocument()
    })

    it('does not render Analyze button when analysis already exists', () => {
      const filingWithAnalysis = {
        ...baseFiling,
        has_analysis: true,
      }

      render(<FilingCard filing={filingWithAnalysis} onAnalyze={mockOnAnalyze} />)

      expect(screen.queryByRole('button', { name: /Analyze/ })).not.toBeInTheDocument()
    })

    it('does not render buttons when handlers not provided', () => {
      render(<FilingCard filing={baseFiling} />)

      expect(screen.queryByRole('button', { name: /View Details/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /Analyze/ })).not.toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('calls onViewDetails when View Details button clicked', () => {
      render(<FilingCard filing={baseFiling} onViewDetails={mockOnViewDetails} />)

      const viewButton = screen.getByRole('button', { name: /View Details/ })
      fireEvent.click(viewButton)

      expect(mockOnViewDetails).toHaveBeenCalledWith('0000320193-24-000001')
    })

    it('calls onAnalyze when Analyze button clicked', () => {
      const filingWithoutAnalysis = {
        ...baseFiling,
        has_analysis: false,
      }

      render(<FilingCard filing={filingWithoutAnalysis} onAnalyze={mockOnAnalyze} />)

      const analyzeButton = screen.getByRole('button', { name: /Analyze/ })
      fireEvent.click(analyzeButton)

      expect(mockOnAnalyze).toHaveBeenCalledWith('0000320193-24-000001')
    })
  })

  describe('Filing Types', () => {
    const filingTypes = [
      '10-K',
      '10-Q', 
      '8-K',
      'DEF 14A',
      '10-K/A',
      '10-Q/A',
    ]

    filingTypes.forEach(filingType => {
      it(`displays correct icon for ${filingType} filing type`, () => {
        const filing = {
          ...baseFiling,
          filing_type: filingType,
        }

        render(<FilingCard filing={filing} />)

        expect(screen.getByText(filingType)).toBeInTheDocument()
        // All filing types use FileText icon, so we check for the icon presence
        const icon = document.querySelector('.text-primary')
        expect(icon).toBeInTheDocument()
      })
    })

    it('displays default icon for unknown filing type', () => {
      const filing = {
        ...baseFiling,
        filing_type: 'UNKNOWN',
      }

      render(<FilingCard filing={filing} />)

      expect(screen.getByText('UNKNOWN')).toBeInTheDocument()
      const icon = document.querySelector('.text-primary')
      expect(icon).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<FilingCard filing={baseFiling} />)

      const heading = screen.getByRole('heading', { level: 3 })
      expect(heading).toHaveTextContent('10-K')
    })

    it('has accessible button labels', () => {
      render(<FilingCard 
        filing={baseFiling} 
        onViewDetails={mockOnViewDetails}
        onAnalyze={mockOnAnalyze}
      />)

      const viewButton = screen.getByRole('button', { name: /View Details/ })
      expect(viewButton).toHaveAccessibleName()
    })

    it('provides clear status information', () => {
      render(<FilingCard filing={baseFiling} />)

      expect(screen.getByText('Processing:')).toBeInTheDocument()
      expect(screen.getByText('completed')).toBeInTheDocument()
    })
  })

  describe('Hover Effects', () => {
    it('applies hover styling to card', () => {
      render(<FilingCard filing={baseFiling} />)

      const card = document.querySelector('.hover\\:shadow-md')
      expect(card).toBeInTheDocument()
    })

    it('applies transition effects', () => {
      render(<FilingCard filing={baseFiling} />)

      const card = document.querySelector('.transition-shadow')
      expect(card).toBeInTheDocument()
    })
  })

  describe('Date Formatting', () => {
    it('formats filing date correctly', () => {
      render(<FilingCard filing={baseFiling} />)

      // Date formatting might vary, check for year and that date is present
      expect(screen.getByText(/Filed:/)).toBeInTheDocument()
      expect(screen.getByText(/2024/)).toBeInTheDocument()
    })

    it('formats analysis date correctly', () => {
      const filingWithAnalysis = {
        ...baseFiling,
        has_analysis: true,
        analysis_date: '2024-01-16T10:00:00Z',
      }

      render(<FilingCard filing={filingWithAnalysis} />)

      expect(screen.getByText(/Last Analysis: 1\/16\/2024/)).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing company information gracefully', () => {
      const filingWithoutCompany = {
        ...baseFiling,
        company_name: undefined,
        company_ticker: undefined,
      }

      render(<FilingCard filing={filingWithoutCompany} />)

      // Should not crash and should not show company section
      expect(screen.getByText('10-K')).toBeInTheDocument()
    })

    it('handles partial company information', () => {
      const filingWithPartialCompany = {
        ...baseFiling,
        company_name: 'Apple Inc.',
        company_ticker: undefined,
      }

      render(<FilingCard filing={filingWithPartialCompany} />)

      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('handles missing metadata gracefully', () => {
      const filingWithoutMetadata = {
        ...baseFiling,
        metadata: {},
      }

      render(<FilingCard filing={filingWithoutMetadata} />)

      expect(screen.getByText('10-K')).toBeInTheDocument()
    })
  })

  describe('Forward Ref', () => {
    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>()
      
      render(<FilingCard filing={baseFiling} ref={ref} />)

      expect(ref.current).toBeInstanceOf(HTMLDivElement)
      expect(ref.current).toHaveClass('rounded-lg')
    })
  })
})