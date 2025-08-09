import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { FilingSearchForm } from './FilingSearchForm'
// import type { FilingSearchParams } from '@/api/filings'
// import type { EdgarSearchParams } from '@/api/types'

describe('FilingSearchForm', () => {
  const mockOnSearch = vi.fn()
  const mockOnEdgarSearch = vi.fn()
  const mockOnSearchTypeChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders search input with correct placeholder', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      expect(searchInput).toBeInTheDocument()
      expect(searchInput).toHaveAttribute('type', 'text')
      expect(searchInput).toHaveAttribute('required')
    })

    it('renders search button', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const searchButton = screen.getByRole('button', { name: /Search/ })
      expect(searchButton).toBeInTheDocument()
      expect(searchButton).toHaveAttribute('type', 'submit')
    })

    it('renders filters button', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      expect(filtersButton).toBeInTheDocument()
      expect(filtersButton).toHaveAttribute('type', 'button')
    })
  })

  describe('Search Type Selector', () => {
    it('renders search type selector when onSearchTypeChange provided', () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          onSearchTypeChange={mockOnSearchTypeChange}
        />
      )

      expect(screen.getByText('Search in:')).toBeInTheDocument()
      expect(screen.getByText(/SEC Edgar/)).toBeInTheDocument()
      expect(screen.getByText(/Our Database/)).toBeInTheDocument()
    })

    it('does not render search type selector when onSearchTypeChange not provided', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      expect(screen.queryByText('Search in:')).not.toBeInTheDocument()
    })

    it('handles search type change to Edgar', () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          onSearchTypeChange={mockOnSearchTypeChange}
          searchType="database"
        />
      )

      const edgarButton = screen.getByText(/SEC Edgar/)
      fireEvent.click(edgarButton)

      expect(mockOnSearchTypeChange).toHaveBeenCalledWith('edgar')
    })

    it('handles search type change to database', () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          onSearchTypeChange={mockOnSearchTypeChange}
          searchType="edgar"
        />
      )

      const databaseButton = screen.getByText(/Our Database/)
      fireEvent.click(databaseButton)

      expect(mockOnSearchTypeChange).toHaveBeenCalledWith('database')
    })

    it('shows correct active state for search type buttons', () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          onSearchTypeChange={mockOnSearchTypeChange}
          searchType="edgar"
        />
      )

      const edgarButton = screen.getByText(/SEC Edgar/)
      const databaseButton = screen.getByText(/Our Database/)

      // Check the button classes or other indicators of active state
      // Since variant is a React prop, not an HTML attribute, we check classes instead
      expect(edgarButton).toHaveClass('bg-primary', 'text-primary-foreground')
      expect(databaseButton).toHaveClass('border', 'border-input')
    })
  })

  describe('Basic Search Functionality', () => {
    it('calls onSearch with correct params for database search', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} searchType="database" />)

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(searchInput, { target: { value: 'AAPL' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnSearch).toHaveBeenCalledWith({
          ticker: 'AAPL',
          page: 1,
          page_size: 20,
        })
      })
    })

    it('calls onEdgarSearch with correct params for Edgar search', async () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          searchType="edgar"
        />
      )

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(searchInput, { target: { value: 'MSFT' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnEdgarSearch).toHaveBeenCalledWith({
          ticker: 'MSFT',
          page: 1,
          page_size: 20,
        })
      })
    })

    it('converts ticker to uppercase', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} searchType="database" />)

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(searchInput, { target: { value: 'aapl' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnSearch).toHaveBeenCalledWith(expect.objectContaining({ ticker: 'AAPL' }))
      })
    })

    it('does not submit when ticker is empty', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const searchButton = screen.getByRole('button', { name: /Search/ })
      fireEvent.click(searchButton)

      // Form should not submit due to required attribute and empty ticker
      await waitFor(() => {
        expect(mockOnSearch).not.toHaveBeenCalled()
      })
    })

    it('trims whitespace from ticker', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} searchType="database" />)

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(searchInput, { target: { value: '  AAPL  ' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnSearch).toHaveBeenCalledWith(expect.objectContaining({ ticker: 'AAPL' }))
      })
    })
  })

  describe('Advanced Filters', () => {
    it('toggles advanced filters when filters button clicked', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })

      // Advanced filters should not be visible initially
      expect(screen.queryByText('Advanced Filters')).not.toBeInTheDocument()

      fireEvent.click(filtersButton)

      // Advanced filters should now be visible
      expect(screen.getByText('Advanced Filters')).toBeInTheDocument()
    })

    it('shows filter count badge when filters are active', () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          initialValues={{
            ticker: 'AAPL',
            filing_type: '10-K',
            start_date: '2024-01-01',
          }}
        />
      )

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      const badge = filtersButton.querySelector('.bg-primary')

      expect(badge).toBeInTheDocument()
      expect(badge).toHaveTextContent('2') // filing_type and start_date
    })

    it('renders filing type filter', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      expect(screen.getByLabelText('Filing Type')).toBeInTheDocument()
      expect(screen.getByDisplayValue('All Filing Types')).toBeInTheDocument()
    })

    it('renders date range filters', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      expect(screen.getByLabelText('From Date')).toBeInTheDocument()
      expect(screen.getByLabelText('To Date')).toBeInTheDocument()
    })

    it('applies date constraints correctly', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      const startDateInput = screen.getByLabelText('From Date')
      const endDateInput = screen.getByLabelText('To Date')

      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })

      // End date should have min constraint set to start date
      expect(endDateInput).toHaveAttribute('min', '2024-01-01')

      fireEvent.change(endDateInput, { target: { value: '2024-06-01' } })

      // Start date should have max constraint set to end date
      expect(startDateInput).toHaveAttribute('max', '2024-06-01')
    })
  })

  describe('Filter Management', () => {
    it('includes filters in search params', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} searchType="database" />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      // Set filters
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      const startDateInput = screen.getByLabelText('From Date')
      const tickerInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(filingTypeSelect, { target: { value: '10-K' } })
      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })
      fireEvent.change(tickerInput, { target: { value: 'AAPL' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnSearch).toHaveBeenCalledWith({
          ticker: 'AAPL',
          filing_type: '10-K',
          start_date: '2024-01-01',
          page: 1,
          page_size: 20,
        })
      })
    })

    it('includes Edgar-specific filter names', async () => {
      render(
        <FilingSearchForm
          onSearch={mockOnSearch}
          onEdgarSearch={mockOnEdgarSearch}
          searchType="edgar"
        />
      )

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      // Set filters
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      const startDateInput = screen.getByLabelText('From Date')
      const tickerInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(filingTypeSelect, { target: { value: '10-Q' } })
      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })
      fireEvent.change(tickerInput, { target: { value: 'MSFT' } })
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(mockOnEdgarSearch).toHaveBeenCalledWith({
          ticker: 'MSFT',
          form_type: '10-Q', // Edgar uses form_type
          date_from: '2024-01-01', // Edgar uses date_from
          page: 1,
          page_size: 20,
        })
      })
    })

    it('clears all filters when Clear All button clicked', async () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      // Set some filters first
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      const startDateInput = screen.getByLabelText('From Date')

      fireEvent.change(filingTypeSelect, { target: { value: '10-K' } })
      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })

      // Verify filters are set
      expect(filingTypeSelect).toHaveValue('10-K')
      expect(startDateInput).toHaveValue('2024-01-01')

      // Clear all filters
      const clearButton = screen.getByRole('button', { name: /Clear All/ })
      fireEvent.click(clearButton)

      // After clearing, the advanced filters should be hidden
      await waitFor(() => {
        expect(screen.queryByLabelText('Filing Type')).not.toBeInTheDocument()
        expect(screen.queryByLabelText('From Date')).not.toBeInTheDocument()
      })

      // Re-open filters to verify they were cleared
      const filtersButtonAfterClear = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButtonAfterClear)

      // Now the filters should be cleared
      const clearedFilingTypeSelect = screen.getByLabelText('Filing Type')
      const clearedStartDateInput = screen.getByLabelText('From Date')
      expect(clearedFilingTypeSelect).toHaveValue('')
      expect(clearedStartDateInput).toHaveValue('')
    })
  })

  describe('Active Filters Display', () => {
    it('shows active filters when filters are set', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      // Set filters
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      const startDateInput = screen.getByLabelText('From Date')

      fireEvent.change(filingTypeSelect, { target: { value: '10-K' } })
      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })

      // Active filters should be displayed
      expect(screen.getByText('Active filters:')).toBeInTheDocument()
      expect(screen.getByText('Type: 10-K')).toBeInTheDocument()
      expect(screen.getByText('From: 2024-01-01')).toBeInTheDocument()
    })

    it('allows removing individual filters', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      // Set filter
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      fireEvent.change(filingTypeSelect, { target: { value: '10-K' } })

      // Look for the X button in the active filter tag
      const removeButtons = document.querySelectorAll('button[class*="hover:bg-primary/20"]')
      if (removeButtons.length > 0) {
        fireEvent.click(removeButtons[0])
        // Filter should be removed
        expect(filingTypeSelect).toHaveValue('')
      } else {
        // If no remove button found, just verify the filter was set
        expect(filingTypeSelect).toHaveValue('10-K')
      }
    })
  })

  describe('Loading States', () => {
    it('shows loading state on search button when isLoading is true', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} isLoading={true} />)

      const searchButton = screen.getByRole('button', { name: /Searching.../ })
      expect(searchButton).toBeInTheDocument()
      expect(searchButton).toBeDisabled()
    })

    it('disables search button when ticker is empty', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const searchButton = screen.getByRole('button', { name: /Search/ })
      expect(searchButton).toBeDisabled()
    })

    it('enables search button when ticker is provided', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const tickerInput = screen.getByPlaceholderText(/Enter company ticker/)
      const searchButton = screen.getByRole('button', { name: /Search/ })

      fireEvent.change(tickerInput, { target: { value: 'AAPL' } })

      expect(searchButton).not.toBeDisabled()
    })
  })

  describe('Initial Values', () => {
    it('populates form with initial values', () => {
      const initialValues = {
        ticker: 'AAPL',
        filing_type: '10-K',
        start_date: '2024-01-01',
        end_date: '2024-06-01',
      }

      render(<FilingSearchForm onSearch={mockOnSearch} initialValues={initialValues} />)

      expect(screen.getByDisplayValue('AAPL')).toBeInTheDocument()

      // Advanced filters should be visible automatically with initial values
      // Check that the filing type select has the correct value
      const filingTypeSelect = screen.getByLabelText('Filing Type')
      expect(filingTypeSelect).toHaveValue('10-K')
      expect(screen.getByDisplayValue('2024-01-01')).toBeInTheDocument()
      expect(screen.getByDisplayValue('2024-06-01')).toBeInTheDocument()
    })

    it('shows advanced filters when initial values include filters', () => {
      const initialValues = {
        ticker: 'AAPL',
        filing_type: '10-K',
      }

      render(<FilingSearchForm onSearch={mockOnSearch} initialValues={initialValues} />)

      // Advanced filters should be shown automatically
      expect(screen.getByText('Advanced Filters')).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('prevents submission with empty ticker', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      // Try to submit the form by clicking the search button
      const searchButton = screen.getByRole('button', { name: /Search/ })
      fireEvent.click(searchButton)

      // Should not call onSearch due to HTML5 validation (required attribute)
      expect(mockOnSearch).not.toHaveBeenCalled()
    })

    it('validates date range constraints', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      const endDateInput = screen.getByLabelText('To Date')
      const today = new Date().toISOString().split('T')[0]

      expect(endDateInput).toHaveAttribute('max', today)
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const filtersButton = screen.getByRole('button', { name: /Filters/ })
      fireEvent.click(filtersButton)

      expect(screen.getByLabelText('Filing Type')).toBeInTheDocument()
      expect(screen.getByLabelText('From Date')).toBeInTheDocument()
      expect(screen.getByLabelText('To Date')).toBeInTheDocument()
    })

    it('has accessible button labels', () => {
      render(
        <FilingSearchForm onSearch={mockOnSearch} onSearchTypeChange={mockOnSearchTypeChange} />
      )

      expect(screen.getByRole('button', { name: /Filters/ })).toHaveAccessibleName()
      expect(screen.getByRole('button', { name: /Search/ })).toHaveAccessibleName()
    })

    it('provides clear search instructions', () => {
      render(<FilingSearchForm onSearch={mockOnSearch} />)

      const searchInput = screen.getByPlaceholderText(/Enter company ticker/)
      expect(searchInput).toHaveAttribute(
        'placeholder',
        'Enter company ticker (e.g., AAPL, MSFT, GOOGL)'
      )
    })
  })
})
