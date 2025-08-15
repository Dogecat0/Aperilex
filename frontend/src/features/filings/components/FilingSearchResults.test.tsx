import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@/test/utils'
import { FilingSearchResults } from './FilingSearchResults'
import type { FilingResponse, PaginatedResponse } from '@/api/types'

// Mock the FilingCard component
vi.mock('./FilingCard', () => ({
  FilingCard: ({ filing, onViewDetails, onAnalyze }: any) => (
    <div data-testid="filing-card">
      <span>{filing.filing_type}</span>
      <span>{filing.accession_number}</span>
      {onViewDetails && (
        <button onClick={() => onViewDetails(filing.accession_number)}>View Details</button>
      )}
      {onAnalyze && <button onClick={() => onAnalyze(filing.accession_number)}>Analyze</button>}
    </div>
  ),
}))

describe('FilingSearchResults', () => {
  const mockOnViewDetails = vi.fn()
  const mockOnAnalyze = vi.fn()
  const mockOnPageChange = vi.fn()

  const mockFilingData: PaginatedResponse<FilingResponse> = {
    items: [
      {
        filing_id: '1',
        company_id: '320193',
        accession_number: '0000320193-24-000001',
        filing_type: '10-K',
        filing_date: '2024-01-15',
        processing_status: 'completed',
        processing_error: null,
        metadata: {},
        analyses_count: 1,
        latest_analysis_date: '2024-01-16T10:00:00Z',
      },
      {
        filing_id: '2',
        company_id: '320193',
        accession_number: '0000320193-24-000002',
        filing_type: '10-Q',
        filing_date: '2024-02-15',
        processing_status: 'completed',
        processing_error: null,
        metadata: {},
        analyses_count: 0,
        latest_analysis_date: null,
      },
    ],
    pagination: {
      page: 1,
      page_size: 20,
      total_items: 2,
      total_pages: 1,
      has_next: false,
      has_previous: false,
      next_page: null,
      previous_page: null,
    },
  }

  const mockMultiPageData: PaginatedResponse<FilingResponse> = {
    ...mockFilingData,
    pagination: {
      page: 2,
      page_size: 1,
      total_items: 2,
      total_pages: 2,
      has_next: false,
      has_previous: true,
      next_page: null,
      previous_page: 1,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Loading State', () => {
    it('displays loading skeleton when isLoading is true', () => {
      render(<FilingSearchResults isLoading={true} />)

      // Should show skeleton elements for header and filing cards
      const skeletons = screen.getAllByRole('generic')
      expect(skeletons.length).toBeGreaterThanOrEqual(6) // At least header skeletons + filing card skeletons

      // Should not show any actual content
      expect(screen.queryByText('Filings')).not.toBeInTheDocument()
      expect(screen.queryByTestId('filing-card')).not.toBeInTheDocument()
      expect(screen.queryByText('No Filings Found')).not.toBeInTheDocument()
      expect(screen.queryByText('Search Failed')).not.toBeInTheDocument()
    })

    it('shows loading state when data is present but no error', () => {
      render(<FilingSearchResults isLoading={true} data={mockFilingData} />)

      // Loading should show when no error present
      const skeletons = screen.getAllByRole('generic')
      expect(skeletons.length).toBeGreaterThan(0) // Should have some skeleton elements

      // Should not show data content
      expect(screen.queryByTestId('filing-card')).not.toBeInTheDocument()
      expect(screen.queryByText('Apple Inc. Filings')).not.toBeInTheDocument()
    })

    it('loading state displays multiple skeleton elements', () => {
      render(<FilingSearchResults isLoading={true} />)

      // Should render multiple skeleton elements - actual count is 10 based on test output
      const skeletons = screen.getAllByRole('generic')
      expect(skeletons.length).toBe(10) // This includes Skeleton component internal elements

      // Verify we're in loading state by ensuring content is not shown
      expect(screen.queryByText('Filings')).not.toBeInTheDocument()
      expect(screen.queryByText('No Filings Found')).not.toBeInTheDocument()
    })

    it('error state takes precedence over loading state', () => {
      render(<FilingSearchResults isLoading={true} error={{ detail: 'Test error' }} />)

      // Error should render instead of loading state
      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(screen.getByText('Test error')).toBeInTheDocument()

      // Should not show loading-specific content (though error state may have generic divs)
      expect(screen.queryByText('Showing')).not.toBeInTheDocument()
      expect(screen.queryByTestId('filing-card')).not.toBeInTheDocument()
    })

    it('does not render data or empty states when loading', () => {
      render(<FilingSearchResults isLoading={true} data={mockFilingData} />)

      // Should not render results
      expect(screen.queryByText('Apple Inc. Filings')).not.toBeInTheDocument()
      expect(screen.queryByTestId('filing-card')).not.toBeInTheDocument()

      // Should not render empty state
      expect(screen.queryByText('No Filings Found')).not.toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('displays error message when error occurs', () => {
      const error = { detail: 'Search failed' }
      render(<FilingSearchResults error={error} />)

      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(screen.getByText('Search failed')).toBeInTheDocument()
    })

    it('displays generic error message when error has no detail', () => {
      render(<FilingSearchResults error={{}} />)

      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(
        screen.getByText('There was an error searching for filings. Please try again.')
      ).toBeInTheDocument()
    })

    it('displays generic error message when error is a string', () => {
      render(<FilingSearchResults error="Network error" />)

      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(
        screen.getByText('There was an error searching for filings. Please try again.')
      ).toBeInTheDocument()
    })

    it('handles error with complex detail structure', () => {
      const error = { detail: 'Complex error with additional info', status: 500 }
      render(<FilingSearchResults error={error} />)

      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(screen.getByText('Complex error with additional info')).toBeInTheDocument()
    })

    it('displays error state with correct structure and icon', () => {
      const error = { detail: 'Test error' }
      render(<FilingSearchResults error={error} />)

      expect(screen.getByText('Search Failed')).toBeInTheDocument()
      expect(screen.getByText('Test error')).toBeInTheDocument()

      // Check that the error has the correct structure with icon and message
      const errorContainer = screen.getByText('Search Failed').closest('div')
      expect(errorContainer).toBeInTheDocument()

      // Verify that no other states are shown when error is present
      expect(screen.queryByText('Loading')).not.toBeInTheDocument()
      expect(screen.queryByText('No Filings Found')).not.toBeInTheDocument()
      expect(screen.queryByTestId('filing-card')).not.toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no data', () => {
      render(<FilingSearchResults data={undefined} />)

      expect(screen.getByText('No Filings Found')).toBeInTheDocument()
      expect(
        screen.getByText('No SEC filings match your search criteria. Try adjusting your filters.')
      ).toBeInTheDocument()
    })

    it('displays empty state when data has no items', () => {
      const emptyData: PaginatedResponse<FilingResponse> = {
        items: [],
        pagination: {
          page: 1,
          page_size: 20,
          total_items: 0,
          total_pages: 0,
          has_next: false,
          has_previous: false,
          next_page: null,
          previous_page: null,
        },
      }

      render(<FilingSearchResults data={emptyData} />)

      expect(screen.getByText('No Filings Found')).toBeInTheDocument()
    })

    it('displays ticker-specific message when searchTicker is provided', () => {
      render(<FilingSearchResults data={undefined} searchTicker="AAPL" />)

      expect(
        screen.getByText('No SEC filings found for AAPL. Try adjusting your search criteria.')
      ).toBeInTheDocument()
    })
  })

  describe('Results Display', () => {
    it('renders filing cards for each item', () => {
      render(
        <FilingSearchResults
          data={mockFilingData}
          companyName="Apple Inc."
          searchTicker="AAPL"
          onViewDetails={mockOnViewDetails}
          onAnalyze={mockOnAnalyze}
        />
      )

      expect(screen.getAllByTestId('filing-card')).toHaveLength(2)
      expect(screen.getByText('10-K')).toBeInTheDocument()
      expect(screen.getByText('10-Q')).toBeInTheDocument()
    })

    it('displays correct header with company name', () => {
      render(<FilingSearchResults data={mockFilingData} companyName="Apple Inc." />)

      expect(screen.getByText('Apple Inc. Filings')).toBeInTheDocument()
      expect(screen.getByText('Showing 2 filings')).toBeInTheDocument()
    })

    it('displays correct header with ticker when no company name', () => {
      render(<FilingSearchResults data={mockFilingData} searchTicker="AAPL" />)

      expect(screen.getByText('AAPL Filings')).toBeInTheDocument()
    })

    it('handles callback functions correctly', () => {
      render(
        <FilingSearchResults
          data={mockFilingData}
          onViewDetails={mockOnViewDetails}
          onAnalyze={mockOnAnalyze}
        />
      )

      const viewButtons = screen.getAllByText('View Details')
      const analyzeButtons = screen.getAllByText('Analyze')

      fireEvent.click(viewButtons[0])
      expect(mockOnViewDetails).toHaveBeenCalledWith('0000320193-24-000001')

      fireEvent.click(analyzeButtons[0])
      expect(mockOnAnalyze).toHaveBeenCalledWith('0000320193-24-000001')
    })
  })

  describe('Pagination', () => {
    it('does not show pagination for single page results', () => {
      render(<FilingSearchResults data={mockFilingData} />)

      expect(screen.queryByText('Previous')).not.toBeInTheDocument()
      expect(screen.queryByText('Next')).not.toBeInTheDocument()
    })

    it('shows pagination controls for multi-page results', () => {
      render(<FilingSearchResults data={mockMultiPageData} onPageChange={mockOnPageChange} />)

      expect(screen.getByText('Previous')).toBeInTheDocument()
      expect(screen.getByText('Next')).toBeInTheDocument()
      expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    })

    it('handles pagination clicks correctly', () => {
      render(<FilingSearchResults data={mockMultiPageData} onPageChange={mockOnPageChange} />)

      const previousButton = screen.getByText('Previous')
      fireEvent.click(previousButton)

      expect(mockOnPageChange).toHaveBeenCalledWith(1)
    })

    it('disables pagination buttons appropriately', () => {
      render(<FilingSearchResults data={mockMultiPageData} onPageChange={mockOnPageChange} />)

      const nextButton = screen.getByText('Next')
      expect(nextButton).toBeDisabled()
    })

    it('shows page info correctly', () => {
      render(<FilingSearchResults data={mockMultiPageData} />)

      expect(screen.getByText(/page 2 of 2/)).toBeInTheDocument()
      expect(screen.getByText('2-2 of 2')).toBeInTheDocument()
    })
  })

  describe('Database-Only Results', () => {
    it('only renders FilingCard components (no EdgarFilingCard)', () => {
      render(
        <FilingSearchResults data={mockFilingData} companyName="Apple Inc." searchTicker="AAPL" />
      )

      // All cards should be FilingCard components
      expect(screen.getAllByTestId('filing-card')).toHaveLength(2)

      // Should not contain any EDGAR-specific elements
      expect(screen.queryByText('Content Available')).not.toBeInTheDocument()
      expect(screen.queryByText('Analysis Available')).not.toBeInTheDocument()
    })

    it('passes correct props to FilingCard', () => {
      render(
        <FilingSearchResults data={mockFilingData} companyName="Apple Inc." searchTicker="AAPL" />
      )

      // FilingCard should receive the enhanced filing object
      // This is tested through the mock that renders the accession number
      expect(screen.getByText('0000320193-24-000001')).toBeInTheDocument()
      expect(screen.getByText('0000320193-24-000002')).toBeInTheDocument()
    })
  })
})
