import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import { FilingMetadata } from './FilingMetadata'
import type { FilingResponse } from '@/api/types'

describe('FilingMetadata', () => {
  const baseFiling: FilingResponse & {
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
      file_size: 2500000,
    },
    analyses_count: 3,
    latest_analysis_date: '2024-01-16T10:00:00Z',
  }

  describe('Basic Rendering', () => {
    it('renders metadata section header', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Filing Information')
      expect(screen.getByText('Filing Information')).toBeInTheDocument()
    })

    it('displays basic filing information', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('Filing Type')).toBeInTheDocument()
      expect(screen.getByText('10-K')).toBeInTheDocument()

      expect(screen.getByText('Filing Date')).toBeInTheDocument()
      expect(screen.getByText('1/15/2024')).toBeInTheDocument()

      expect(screen.getByText('Accession Number')).toBeInTheDocument()
      expect(screen.getByText('0000320193-24-000001')).toBeInTheDocument()
    })

    it('displays accession number in monospace font', () => {
      render(<FilingMetadata filing={baseFiling} />)

      const accessionElement = screen.getByText('0000320193-24-000001')
      expect(accessionElement).toHaveClass('font-mono')
    })
  })

  describe('Company Information', () => {
    it('displays company information when provided', () => {
      const filingWithCompany = {
        ...baseFiling,
        company_name: 'Apple Inc.',
        company_ticker: 'AAPL',
      }

      render(<FilingMetadata filing={filingWithCompany} />)

      expect(screen.getByText('Company')).toBeInTheDocument()
      expect(screen.getByText('Apple Inc. (AAPL)')).toBeInTheDocument()
    })

    it('displays company name without ticker when ticker not available', () => {
      const filingWithCompanyOnly = {
        ...baseFiling,
        company_name: 'Apple Inc.',
      }

      render(<FilingMetadata filing={filingWithCompanyOnly} />)

      expect(screen.getByText('Company')).toBeInTheDocument()
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('does not display company section when company info not available', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.queryByText('Company')).not.toBeInTheDocument()
    })
  })

  describe('Processing Status', () => {
    it('displays completed status with correct styling', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('Processing Status')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()

      // Check for green styling
      const statusElement = document.querySelector('.text-green-600.bg-green-50')
      expect(statusElement).toBeInTheDocument()
    })

    it('displays failed status with correct styling', () => {
      const failedFiling = {
        ...baseFiling,
        processing_status: 'failed' as const,
      }

      render(<FilingMetadata filing={failedFiling} />)

      expect(screen.getByText('Failed')).toBeInTheDocument()

      // Check for red styling
      const statusElement = document.querySelector('.text-red-600.bg-red-50')
      expect(statusElement).toBeInTheDocument()
    })

    it('displays processing status with correct styling', () => {
      const processingFiling = {
        ...baseFiling,
        processing_status: 'processing' as const,
      }

      render(<FilingMetadata filing={processingFiling} />)

      expect(screen.getByText('Processing')).toBeInTheDocument()

      // Check for blue styling
      const statusElement = document.querySelector('.text-blue-600.bg-blue-50')
      expect(statusElement).toBeInTheDocument()
    })

    it('displays pending status with correct styling', () => {
      const pendingFiling = {
        ...baseFiling,
        processing_status: 'pending' as const,
      }

      render(<FilingMetadata filing={pendingFiling} />)

      expect(screen.getByText('Pending')).toBeInTheDocument()

      // Check for yellow styling
      const statusElement = document.querySelector('.text-yellow-600.bg-yellow-50')
      expect(statusElement).toBeInTheDocument()
    })

    it('capitalizes status text correctly', () => {
      render(<FilingMetadata filing={baseFiling} />)

      // Should be "Completed" not "completed"
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.queryByText('completed')).not.toBeInTheDocument()
    })
  })

  describe('Processing Errors', () => {
    it('displays processing error when present', () => {
      const errorFiling = {
        ...baseFiling,
        processing_status: 'failed' as const,
        processing_error: 'Failed to parse financial statements due to malformed XML',
      }

      render(<FilingMetadata filing={errorFiling} />)

      expect(screen.getByText('Processing Error')).toBeInTheDocument()
      expect(
        screen.getByText('Failed to parse financial statements due to malformed XML')
      ).toBeInTheDocument()

      // Check error styling
      const errorSection = document.querySelector('.bg-red-50.border-red-200')
      expect(errorSection).toBeInTheDocument()
    })

    it('does not display error section when no error', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.queryByText('Processing Error')).not.toBeInTheDocument()
    })
  })

  describe('Analysis Summary', () => {
    it('displays analysis summary when analysis data available', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('Analysis Summary')).toBeInTheDocument()
      expect(screen.getByText('Total Analyses')).toBeInTheDocument()
      // Look for analyses count in the context of Total Analyses
      const totalAnalysesSection = screen.getByText('Total Analyses').parentElement
      expect(totalAnalysesSection).toHaveTextContent('3')
      expect(screen.getByText('Latest Analysis')).toBeInTheDocument()
      expect(screen.getByText('1/16/2024')).toBeInTheDocument()
    })

    it('displays analysis count when available', () => {
      const filingWithAnalysisCount = {
        ...baseFiling,
        analyses_count: 5,
      }

      render(<FilingMetadata filing={filingWithAnalysisCount} />)

      expect(screen.getByText('Total Analyses')).toBeInTheDocument()
      // Look for analyses count in the context of Total Analyses
      const totalAnalysesSection = screen.getByText('Total Analyses').parentElement
      expect(totalAnalysesSection).toHaveTextContent('5')
    })

    it('displays latest analysis date when available', () => {
      const filingWithLatestAnalysis = {
        ...baseFiling,
        latest_analysis_date: '2024-02-01T15:30:00Z',
      }

      render(<FilingMetadata filing={filingWithLatestAnalysis} />)

      expect(screen.getByText('Latest Analysis')).toBeInTheDocument()
      expect(screen.getByText('2/1/2024')).toBeInTheDocument()
    })

    it('does not display analysis summary when no analysis data', () => {
      const filingWithoutAnalysis = {
        ...baseFiling,
        analyses_count: undefined,
        latest_analysis_date: undefined,
      }

      render(<FilingMetadata filing={filingWithoutAnalysis} />)

      expect(screen.queryByText('Analysis Summary')).not.toBeInTheDocument()
    })

    it('displays partial analysis summary when only some data available', () => {
      const filingWithPartialAnalysis = {
        ...baseFiling,
        analyses_count: 2,
        latest_analysis_date: undefined,
      }

      render(<FilingMetadata filing={filingWithPartialAnalysis} />)

      expect(screen.getByText('Analysis Summary')).toBeInTheDocument()
      expect(screen.getByText('Total Analyses')).toBeInTheDocument()
      // Look for analyses count in the context of Total Analyses
      const totalAnalysesSection = screen.getByText('Total Analyses').parentElement
      expect(totalAnalysesSection).toHaveTextContent('2')
      expect(screen.queryByText('Latest Analysis')).not.toBeInTheDocument()
    })
  })

  describe('Additional Metadata', () => {
    it('displays additional metadata when available', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('Additional Information')).toBeInTheDocument()
      expect(screen.getByText('period end date')).toBeInTheDocument()
      expect(screen.getByText('2023-12-31')).toBeInTheDocument()
      expect(screen.getByText('sec url')).toBeInTheDocument()
      expect(screen.getByText('https://www.sec.gov/test')).toBeInTheDocument()
      expect(screen.getByText('file size')).toBeInTheDocument()
      expect(screen.getByText('2500000')).toBeInTheDocument()
    })

    it('converts underscore-separated keys to readable format', () => {
      const filingWithMetadata = {
        ...baseFiling,
        metadata: {
          fiscal_year_end: '12-31',
          total_assets: 365725000000,
        },
      }

      render(<FilingMetadata filing={filingWithMetadata} />)

      expect(screen.getByText('fiscal year end')).toBeInTheDocument()
      expect(screen.getByText('total assets')).toBeInTheDocument()
    })

    it('handles null values in metadata', () => {
      const filingWithNullMetadata = {
        ...baseFiling,
        metadata: {
          period_end_date: null,
          sec_url: 'https://www.sec.gov/test',
        },
      }

      render(<FilingMetadata filing={filingWithNullMetadata} />)

      expect(screen.getByText('N/A')).toBeInTheDocument()
      expect(screen.getByText('https://www.sec.gov/test')).toBeInTheDocument()
    })

    it('does not display additional metadata when empty', () => {
      const filingWithoutMetadata = {
        ...baseFiling,
        metadata: {},
      }

      render(<FilingMetadata filing={filingWithoutMetadata} />)

      expect(screen.queryByText('Additional Information')).not.toBeInTheDocument()
    })

    it('handles different value types in metadata', () => {
      const filingWithVariedMetadata = {
        ...baseFiling,
        metadata: {
          is_amended: true,
          version_number: 1,
          description: 'Annual report',
          revenue: 365725000000.5,
        },
      }

      render(<FilingMetadata filing={filingWithVariedMetadata} />)

      expect(screen.getByText('true')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('Annual report')).toBeInTheDocument()
      expect(screen.getByText('365725000000.5')).toBeInTheDocument()
    })
  })

  describe('Layout and Styling', () => {
    it('uses proper grid layout for information display', () => {
      render(<FilingMetadata filing={baseFiling} />)

      const gridContainer = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2')
      expect(gridContainer).toBeInTheDocument()
    })

    it('applies correct spacing between sections', () => {
      render(<FilingMetadata filing={baseFiling} />)

      const spacedElements = document.querySelectorAll('.space-y-4, .space-y-3, .space-y-2')
      expect(spacedElements.length).toBeGreaterThan(0)
    })

    it('applies border styling to status indicators', () => {
      render(<FilingMetadata filing={baseFiling} />)

      const statusBadge = document.querySelector('.rounded-md.text-xs.font-medium')
      expect(statusBadge).toBeInTheDocument()
    })
  })

  describe('Icons', () => {
    it('displays appropriate icons for each information type', () => {
      render(<FilingMetadata filing={baseFiling} />)

      // Check for various icons (Lucide React components)
      const iconElements = document.querySelectorAll('svg')
      expect(iconElements.length).toBeGreaterThan(0)
    })

    it('uses database icon for main header', () => {
      render(<FilingMetadata filing={baseFiling} />)

      // The Database icon should be present in the header
      const headerSection = screen.getByText('Filing Information').closest('h3')
      expect(headerSection).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<FilingMetadata filing={baseFiling} />)

      const heading = screen.getByRole('heading', { level: 3 })
      expect(heading).toHaveTextContent('Filing Information')
    })

    it('uses semantic HTML structure', () => {
      render(<FilingMetadata filing={baseFiling} />)

      // Should use proper div structure with appropriate classes
      const container = document.querySelector('.rounded-lg.border.bg-card.p-6')
      expect(container).toBeInTheDocument()
    })

    it('provides clear labels for all information', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('Filing Type')).toBeInTheDocument()
      expect(screen.getByText('Filing Date')).toBeInTheDocument()
      expect(screen.getByText('Accession Number')).toBeInTheDocument()
      expect(screen.getByText('Processing Status')).toBeInTheDocument()
    })
  })

  describe('Date Formatting', () => {
    it('formats filing date correctly', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('1/15/2024')).toBeInTheDocument()
    })

    it('formats analysis date correctly', () => {
      render(<FilingMetadata filing={baseFiling} />)

      expect(screen.getByText('1/16/2024')).toBeInTheDocument()
    })

    it('handles different date formats in metadata', () => {
      const filingWithDateMetadata = {
        ...baseFiling,
        metadata: {
          period_end_date: '2023-12-31',
          last_updated: '2024-01-15T10:30:00Z',
        },
      }

      render(<FilingMetadata filing={filingWithDateMetadata} />)

      expect(screen.getByText('2023-12-31')).toBeInTheDocument()
      expect(screen.getByText('2024-01-15T10:30:00Z')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing required fields gracefully', () => {
      const minimalFiling = {
        filing_id: '1',
        company_id: '320193',
        accession_number: '0000320193-24-000001',
        filing_type: '10-K',
        filing_date: '2024-01-15',
        processing_status: 'completed' as const,
        processing_error: null,
        metadata: {},
      }

      render(<FilingMetadata filing={minimalFiling} />)

      expect(screen.getByText('Filing Information')).toBeInTheDocument()
      expect(screen.getByText('10-K')).toBeInTheDocument()
    })

    it('handles very long metadata values', () => {
      const filingWithLongMetadata = {
        ...baseFiling,
        metadata: {
          very_long_url:
            'https://www.sec.gov/very/long/path/to/some/filing/document/that/has/an/extremely/long/url/structure.htm',
        },
      }

      render(<FilingMetadata filing={filingWithLongMetadata} />)

      const longValue = screen.getByText(/https:\/\/www\.sec\.gov\/very\/long/)
      expect(longValue).toHaveClass('break-all')
    })

    it('handles zero analysis count', () => {
      const filingWithZeroAnalyses = {
        ...baseFiling,
        analyses_count: 0,
      }

      render(<FilingMetadata filing={filingWithZeroAnalyses} />)

      expect(screen.getByText('Total Analyses')).toBeInTheDocument()
      // Look for analyses count in the context of Total Analyses
      const totalAnalysesSection = screen.getByText('Total Analyses').parentElement
      expect(totalAnalysesSection).toHaveTextContent('0')
    })
  })
})
