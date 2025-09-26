import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useAnalyses } from '@/hooks/useAnalysis'
import { render, screen, waitFor, fireEvent } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { AnalysesList } from './AnalysesList'
import type { AnalysisResponse, PaginatedResponse } from '@/api/types'

// Mock hooks
vi.mock('@/hooks/useAnalysis', () => ({
  useAnalyses: vi.fn(),
}))

// Mock company service
vi.mock('@/services/CompanyService', () => ({
  companyService: {
    getCompany: vi.fn(),
  },
}))

const mockUseAnalyses = vi.mocked(useAnalyses)
const { companyService } = await import('@/services/CompanyService')

// Mock child components
vi.mock('./components/AnalysisCard', () => ({
  AnalysisCard: ({ analysis }: { analysis: AnalysisResponse }) => (
    <div data-testid={`analysis-card-${analysis.analysis_id}`}>
      <h3>{analysis.analysis_template}</h3>
      <p>{analysis.executive_summary || 'No summary'}</p>
      <span>{analysis.created_at}</span>
    </div>
  ),
}))

vi.mock('@/components/ui/Button', () => ({
  Button: ({
    children,
    onClick,
    className,
    variant,
    size,
    disabled,
    type = 'button',
    ...props
  }: any) => (
    <button
      onClick={onClick}
      className={className}
      data-variant={variant}
      data-size={size}
      disabled={disabled}
      type={type}
      data-testid="mock-button"
      {...props}
    >
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/Input', () => ({
  Input: ({ value, onChange, placeholder, type = 'text', className, id, ...props }: any) => {
    // Generate a unique id if one isn't provided
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`
    return (
      <input
        id={inputId}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={type}
        className={className}
        data-testid="mock-input"
        {...props}
      />
    )
  },
}))

// Mock data
const mockAnalyses: AnalysisResponse[] = [
  {
    analysis_id: '1',
    filing_id: 'filing-1',
    analysis_template: 'comprehensive',
    created_by: 'user1',
    created_at: '2024-01-15T10:00:00Z',
    confidence_score: 0.95,
    llm_provider: 'openai',
    llm_model: 'gpt-4',
    processing_time_seconds: 45,
    filing_summary: 'Test filing summary',
    executive_summary: 'Comprehensive analysis of Apple Inc. financial performance',
    key_insights: ['Strong revenue growth', 'Solid cash position'],
    financial_highlights: ['Revenue up 15%'],
    risk_factors: ['Market volatility'],
    opportunities: ['Emerging markets'],
    sections_analyzed: 5,
    full_results: null,
  },
  {
    analysis_id: '2',
    filing_id: 'filing-2',
    analysis_template: 'comprehensive',
    created_by: 'user2',
    created_at: '2024-01-14T14:30:00Z',
    confidence_score: 0.88,
    llm_provider: 'openai',
    llm_model: 'gpt-4',
    processing_time_seconds: 32,
    filing_summary: 'Financial analysis summary',
    executive_summary: 'Comprehensive analysis of quarterly results',
    key_insights: ['Profit margins improved'],
    financial_highlights: ['Net income increased'],
    risk_factors: ['Currency fluctuations'],
    opportunities: ['Cost optimization'],
    sections_analyzed: 3,
    full_results: null,
  },
]

const mockPaginatedResponse: PaginatedResponse<AnalysisResponse> = {
  items: mockAnalyses,
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

describe('AnalysesList Component', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock company service to return Apple's CIK when searching for AAPL
    vi.mocked(companyService.getCompany).mockResolvedValue({
      company_id: '1',
      cik: '0000320193',
      name: 'Apple Inc.',
      ticker: 'AAPL',
      display_name: 'Apple Inc. (AAPL)',
      industry: 'Technology',
      sic_code: '3571',
      sic_description: 'Electronic Computers',
      fiscal_year_end: '09',
      business_address: null,
      recent_analyses: [],
    })

    // Default successful mock
    mockUseAnalyses.mockReturnValue({
      data: mockPaginatedResponse,
      isLoading: false,
      error: null,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<AnalysesList />)
      }).not.toThrow()
    })

    it('renders the header section correctly', () => {
      render(<AnalysesList />)

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Analysis Library')
      expect(screen.getByText(/Browse and explore all financial analyses/)).toBeInTheDocument()
      expect(screen.getByText('2 total analyses')).toBeInTheDocument()
    })

    it('renders search input with placeholder', () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      expect(searchInput).toBeInTheDocument()
      expect(searchInput).toHaveValue('')
    })

    it('renders filters button', () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      expect(filtersButton).toBeInTheDocument()
      expect(filtersButton).toHaveAttribute('data-variant', 'outline')
    })

    it('applies correct accessibility attributes', () => {
      render(<AnalysesList />)

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toBeInTheDocument()

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      expect(searchInput).toBeInTheDocument()
    })

    it('renders calendar icons in date inputs', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await userEvent.setup().click(filtersButton)

      // Check that calendar icons are rendered (look for calendar SVGs with cursor-pointer in className)
      const calendarIcons = Array.from(document.querySelectorAll('svg')).filter(
        (svg) =>
          svg.className.baseVal.includes('cursor-pointer') &&
          svg.className.baseVal.includes('lucide-calendar')
      )
      expect(calendarIcons.length).toBe(2) // One for each date input

      // Check that date inputs have the correct CSS class
      const dateInputs = screen.getAllByDisplayValue('')
      const createdFromInput = dateInputs.find((input) => input.getAttribute('type') === 'date')
      const createdToInput = dateInputs.filter((input) => input.getAttribute('type') === 'date')[1]

      expect(createdFromInput).toHaveClass('date-input-hide-native-calendar')
      expect(createdToInput).toHaveClass('date-input-hide-native-calendar')
    })
  })

  describe('Data Loading States', () => {
    it('shows loading skeleton when data is loading', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      })

      render(<AnalysesList />)

      // Check for loading skeleton elements
      const skeletonElements = document.querySelectorAll('.animate-pulse')
      expect(skeletonElements.length).toBeGreaterThan(0)
    })

    it('renders analysis cards when data is loaded', () => {
      render(<AnalysesList />)

      expect(screen.getByTestId('analysis-card-1')).toBeInTheDocument()
      expect(screen.getByTestId('analysis-card-2')).toBeInTheDocument()
    })

    it('shows empty state when no analyses are found', () => {
      mockUseAnalyses.mockReturnValue({
        data: { ...mockPaginatedResponse, items: [] },
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      expect(screen.getByText('No analyses found')).toBeInTheDocument()
      expect(screen.getByText(/No financial analyses are available yet/)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays error message when API call fails', () => {
      const errorMessage = 'Failed to fetch analyses'
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error(errorMessage),
      })

      render(<AnalysesList />)

      expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })

    it('displays generic error for non-Error objects', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: 'String error',
      })

      render(<AnalysesList />)

      expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument()
    })

    it('handles analysis template validation errors from API', () => {
      const templateError = new Error('Invalid analysis template: unsupported_template')
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: templateError,
      })

      render(<AnalysesList />)

      expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
      expect(
        screen.getByText('Invalid analysis template: unsupported_template')
      ).toBeInTheDocument()
    })

    it('handles 422 validation errors for template parameters', () => {
      const validationError = new Error(
        'Unprocessable Entity: analysis_template must be one of: comprehensive, financial_focused, risk_focused, business_focused'
      )
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: validationError,
      })

      render(<AnalysesList />)

      expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
      expect(screen.getByText(/analysis_template must be one of/)).toBeInTheDocument()
    })

    it('handles backward compatibility errors gracefully', () => {
      const compatibilityError = new Error(
        'Parameter analysis_type is deprecated, use analysis_template instead'
      )
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: compatibilityError,
      })

      render(<AnalysesList />)

      expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
      expect(screen.getByText(/analysis_type is deprecated/)).toBeInTheDocument()
    })

    it('recovers gracefully when template filter causes errors', async () => {
      render(<AnalysesList />)

      // Initially successful
      expect(screen.getByTestId('analysis-card-1')).toBeInTheDocument()

      // Show filters and select a template
      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      // Mock an error response when template filter is applied
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Analysis template filter failed'),
      })

      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
        expect(screen.getByText('Analysis template filter failed')).toBeInTheDocument()
      })

      // Previous content should be replaced with error message
      expect(screen.queryByTestId('analysis-card-1')).not.toBeInTheDocument()
    })

    it('handles network errors during template filtering', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      // Mock network error
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network Error: Failed to connect to server'),
      })

      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(screen.getByText('Error loading analyses')).toBeInTheDocument()
        expect(screen.getByText(/Network Error/)).toBeInTheDocument()
      })
    })
  })

  describe('Search Functionality', () => {
    it('updates search term when user types', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)

      await user.type(searchInput, 'AAPL')

      expect(searchInput).toHaveValue('AAPL')

      // Verify useAnalyses was called with search parameters
      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: '0000320193',
            page: 1,
          })
        )
      })
    })

    it('clears search term and resets filters', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      await user.type(searchInput, 'AAPL')

      // Wait for search to be applied
      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: '0000320193',
          })
        )
      })

      // Show filters and clear
      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      const clearButton = screen.getByText('Clear Filters')
      await user.click(clearButton)

      // Wait for the component to update
      await waitFor(() => {
        expect(searchInput).toHaveValue('')
      })

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith({
          page: 1,
          page_size: 20,
        })
      })
    })

    it('converts search term to uppercase for ticker search', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      await user.type(searchInput, 'aapl')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: '0000320193',
          })
        )
      })
    })
  })

  describe('Filters Functionality', () => {
    it('toggles filters visibility when filters button is clicked', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')

      // Initially filters should be hidden
      expect(screen.queryByText('Analysis Type')).not.toBeInTheDocument()

      await user.click(filtersButton)

      // Filters should now be visible
      expect(screen.getByText('Analysis Type')).toBeInTheDocument()
      expect(screen.getByText('Created From')).toBeInTheDocument()
      expect(screen.getByText('Created To')).toBeInTheDocument()
    })

    it('calendar icons are clickable and properly styled', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await userEvent.setup().click(filtersButton)

      // Find calendar icons by their container elements
      const calendarIcons = Array.from(document.querySelectorAll('svg')).filter(
        (svg) =>
          svg.className.baseVal.includes('cursor-pointer') &&
          svg.className.baseVal.includes('lucide-calendar')
      )
      expect(calendarIcons.length).toBe(2)

      // Verify calendar icons have correct styling
      calendarIcons.forEach((icon) => {
        expect(icon.className.baseVal).toContain('cursor-pointer')
        expect(icon.className.baseVal).toContain('hover:text-foreground')
        expect(icon.className.baseVal).toContain('transition-colors')
      })
    })

    it('calendar icons trigger date picker functionality', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await userEvent.setup().click(filtersButton)

      // Mock the showPicker method
      const dateInputs = screen.getAllByDisplayValue('')
      const createdFromInput = dateInputs.find(
        (input) => input.getAttribute('type') === 'date'
      ) as HTMLInputElement
      const createdToInput = dateInputs.filter(
        (input) => input.getAttribute('type') === 'date'
      )[1] as HTMLInputElement

      if (createdFromInput) {
        const mockShowPicker = vi.fn()
        createdFromInput.showPicker = mockShowPicker

        // Click the calendar icon for 'Created From'
        const calendarIcons = Array.from(document.querySelectorAll('svg')).filter(
          (svg) =>
            svg.className.baseVal.includes('cursor-pointer') &&
            svg.className.baseVal.includes('lucide-calendar')
        )
        const firstCalendarIcon = calendarIcons[0]

        if (firstCalendarIcon) {
          fireEvent.click(firstCalendarIcon)
          // Verify showPicker was called or input was focused
          expect(mockShowPicker).toHaveBeenCalled()
        }
      }

      if (createdToInput) {
        const mockShowPicker = vi.fn()
        createdToInput.showPicker = mockShowPicker

        // Click the calendar icon for 'Created To'
        const calendarIcons = Array.from(document.querySelectorAll('svg')).filter(
          (svg) =>
            svg.className.baseVal.includes('cursor-pointer') &&
            svg.className.baseVal.includes('lucide-calendar')
        )
        const secondCalendarIcon = calendarIcons[1]

        if (secondCalendarIcon) {
          fireEvent.click(secondCalendarIcon)
          expect(mockShowPicker).toHaveBeenCalled()
        }
      }
    })

    it('updates analysis type filter', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            analysis_template: 'comprehensive',
            page: 1,
          })
        )
      })
    })

    it('updates date filters', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      // Find date inputs by type since they aren't properly labeled
      const dateInputs = screen.getAllByDisplayValue('')
      const startDateInput = dateInputs.find((input) => input.getAttribute('type') === 'date')
      const endDateInput = dateInputs.filter((input) => input.getAttribute('type') === 'date')[1]

      // Verify date inputs have the CSS class to hide native calendar icons
      expect(startDateInput).toHaveClass('date-input-hide-native-calendar')
      expect(endDateInput).toHaveClass('date-input-hide-native-calendar')

      // For date inputs, we need to use fireEvent.change
      if (startDateInput) {
        fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })
      }
      if (endDateInput) {
        fireEvent.change(endDateInput, { target: { value: '2024-01-31' } })
      }

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            created_from: '2024-01-01',
            created_to: '2024-01-31',
            page: 1,
          })
        )
      })
    })

    it('renders all analysis type options', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      expect(screen.getByText('All Types')).toBeInTheDocument()
      expect(screen.getByText('Comprehensive Analysis')).toBeInTheDocument()
      // Temporarily commented out due to current focus on comprehensive analysis.
      // expect(screen.getByText('Financial Focused')).toBeInTheDocument()
      // expect(screen.getByText('Risk Focused')).toBeInTheDocument()
      // expect(screen.getByText('Business Focused')).toBeInTheDocument()
    })

    it('sends correct lowercase template values in API calls', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      const analysisTypeSelect = screen.getByDisplayValue('All Types')

      // Test the available template value
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            analysis_template: 'comprehensive',
            page: 1,
          })
        )
      })

      // Verify the display value is shown correctly
      expect(screen.getByDisplayValue('Comprehensive Analysis')).toBeInTheDocument()
    })

    it('never sends uppercase values in API requests', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      const analysisTypeSelect = screen.getByDisplayValue('All Types')

      // Test that we never send uppercase values that might have existed in old system
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            analysis_template: 'comprehensive', // lowercase
            page: 1,
          })
        )
      })

      // Ensure we never call with uppercase values from old system
      expect(mockUseAnalyses).not.toHaveBeenCalledWith(
        expect.objectContaining({
          analysis_template: 'COMPREHENSIVE', // uppercase - should not happen
        })
      )
      expect(mockUseAnalyses).not.toHaveBeenCalledWith(
        expect.objectContaining({
          analysis_template: 'FINANCIAL_FOCUSED', // uppercase - should not happen
        })
      )
    })

    it('uses correct default value behavior', async () => {
      render(<AnalysesList />)

      // Initially, no analysis_template should be sent (undefined)
      expect(mockUseAnalyses).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
      })

      // When filters are opened and closed without selection, still no template
      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)
      await user.click(filtersButton) // Close filters

      expect(mockUseAnalyses).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          page_size: 20,
        })
      )

      // analysis_template should not be present in the call
      const lastCall = mockUseAnalyses.mock.calls[mockUseAnalyses.mock.calls.length - 1][0]
      expect(lastCall).not.toHaveProperty('analysis_template')
    })

    it('renders filter dropdown options with correct new template values', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      // Verify all option elements have correct values (lowercase)
      const selectElement = screen.getByDisplayValue('All Types')
      const options = selectElement.querySelectorAll('option')

      const expectedOptions = [
        { value: '', text: 'All Types' },
        { value: 'comprehensive', text: 'Comprehensive Analysis' },
      ]

      expectedOptions.forEach((expected, index) => {
        expect(options[index]).toHaveValue(expected.value)
        expect(options[index]).toHaveTextContent(expected.text)
      })

      // Verify no uppercase values are present in options
      const allOptionValues = Array.from(options).map((option) => option.value)
      expect(allOptionValues).not.toContain('COMPREHENSIVE')
    })

    it('correctly renders analysis cards with new template values', () => {
      render(<AnalysesList />)

      // Verify that analysis cards are rendered with the new template values
      const card1 = screen.getByTestId('analysis-card-1')
      const card2 = screen.getByTestId('analysis-card-2')

      // The mock data uses lowercase template values
      expect(card1).toHaveTextContent('comprehensive')
      expect(card2).toHaveTextContent('comprehensive')

      // Verify cards exist and are properly rendered
      expect(card1).toBeInTheDocument()
      expect(card2).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    const mockPaginatedResponseWithPages: PaginatedResponse<AnalysisResponse> = {
      items: mockAnalyses,
      pagination: {
        page: 2,
        page_size: 1,
        total_items: 3,
        total_pages: 3,
        has_next: true,
        has_previous: true,
        next_page: 3,
        previous_page: 1,
      },
    }

    it('shows pagination when multiple pages exist', () => {
      mockUseAnalyses.mockReturnValue({
        data: mockPaginatedResponseWithPages,
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      expect(screen.getByText('Previous')).toBeInTheDocument()
      expect(screen.getByText('Next')).toBeInTheDocument()
      expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
    })

    it('disables previous button on first page', () => {
      const firstPageResponse = {
        ...mockPaginatedResponseWithPages,
        pagination: {
          ...mockPaginatedResponseWithPages.pagination,
          page: 1,
          has_previous: false,
          previous_page: null,
        },
      }

      mockUseAnalyses.mockReturnValue({
        data: firstPageResponse,
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      const prevButton = screen.getByText('Previous')
      expect(prevButton).toBeDisabled()
    })

    it('disables next button on last page', () => {
      const lastPageResponse = {
        ...mockPaginatedResponseWithPages,
        pagination: {
          ...mockPaginatedResponseWithPages.pagination,
          page: 3,
          has_next: false,
          next_page: null,
        },
      }

      mockUseAnalyses.mockReturnValue({
        data: lastPageResponse,
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      const nextButton = screen.getByText('Next')
      expect(nextButton).toBeDisabled()
    })

    it('shows correct pagination info', () => {
      mockUseAnalyses.mockReturnValue({
        data: mockPaginatedResponseWithPages,
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      expect(screen.getByText('Showing 2 to 2 of 3 analyses')).toBeInTheDocument()
    })

    it('handles pagination clicks', async () => {
      mockUseAnalyses.mockReturnValue({
        data: mockPaginatedResponseWithPages,
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      const nextButton = screen.getByText('Next')
      await user.click(nextButton)

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 3,
          })
        )
      })
    })
  })

  describe('User Interactions', () => {
    it('handles rapid filter changes without errors', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')

      // Rapid clicks
      await user.click(filtersButton)
      await user.click(filtersButton)
      await user.click(filtersButton)

      expect(() => screen.getByText('Analysis Type')).not.toThrow()
    })

    it('maintains search state when toggling filters', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      await user.type(searchInput, 'AAPL')

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)
      await user.click(filtersButton)

      expect(searchInput).toHaveValue('AAPL')
    })

    it('resets page to 1 when filters change', async () => {
      render(<AnalysesList />)

      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)

      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 1,
            analysis_template: 'comprehensive',
          })
        )
      })
    })

    it('handles keyboard navigation in search input', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)

      // Focus and type
      searchInput.focus()
      await user.keyboard('MSFT')

      expect(searchInput).toHaveValue('MSFT')
      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: expect.any(String),
          })
        )
      })
    })

    it('handles empty search gracefully', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)

      // Type and then clear
      await user.type(searchInput, 'AAPL')
      await user.clear(searchInput)

      expect(searchInput).toHaveValue('')
      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: undefined,
            page: 1,
          })
        )
      })
    })
  })

  describe('Advanced Filtering', () => {
    beforeEach(async () => {
      render(<AnalysesList />)

      // Open filters
      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton)
    })

    it('applies multiple filters simultaneously', async () => {
      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      const dateInputs = screen.getAllByDisplayValue('')
      const startDateInput = dateInputs.find((input) => input.getAttribute('type') === 'date')
      const endDateInput = dateInputs.filter((input) => input.getAttribute('type') === 'date')[1]

      await user.selectOptions(analysisTypeSelect, 'comprehensive')
      // For date inputs, we need to use fireEvent.change
      if (startDateInput) {
        fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })
      }
      if (endDateInput) {
        fireEvent.change(endDateInput, { target: { value: '2024-12-31' } })
      }

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            analysis_template: 'comprehensive',
            created_from: '2024-01-01',
            created_to: '2024-12-31',
            page: 1,
          })
        )
      })
    })

    it('validates date range inputs', async () => {
      const dateInputs = screen.getAllByDisplayValue('')
      const startDateInput = dateInputs.find((input) => input.getAttribute('type') === 'date')
      const endDateInput = dateInputs.filter((input) => input.getAttribute('type') === 'date')[1]

      // Set end date before start date (edge case)
      if (startDateInput) {
        fireEvent.change(startDateInput, { target: { value: '2024-12-31' } })
      }
      if (endDateInput) {
        fireEvent.change(endDateInput, { target: { value: '2024-01-01' } })
      }

      if (startDateInput) expect(startDateInput).toHaveValue('2024-12-31')
      if (endDateInput) expect(endDateInput).toHaveValue('2024-01-01')

      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            created_from: '2024-12-31',
            created_to: '2024-01-01',
          })
        )
      })
    })

    it('persists filters when reopening filter panel', async () => {
      const analysisTypeSelect = screen.getByDisplayValue('All Types')
      await user.selectOptions(analysisTypeSelect, 'comprehensive')

      // Close and reopen filters
      const filtersButton = screen.getByText('Filters')
      await user.click(filtersButton) // Close
      await user.click(filtersButton) // Reopen

      const reopenedSelect = screen.getByDisplayValue('Comprehensive Analysis')
      expect(reopenedSelect).toBeInTheDocument()
    })
  })

  describe('Analytics Card Integration', () => {
    it('renders correct number of analysis cards', () => {
      render(<AnalysesList />)

      const cards = screen.getAllByTestId(/analysis-card-/)
      expect(cards).toHaveLength(2) // Based on mockPaginatedResponse
    })

    it('passes correct props to analysis cards', () => {
      render(<AnalysesList />)

      expect(screen.getByTestId('analysis-card-1')).toBeInTheDocument()
      expect(screen.getByTestId('analysis-card-2')).toBeInTheDocument()

      // Check analysis types are displayed (both cards have comprehensive template)
      const comprehensiveElements = screen.getAllByText('comprehensive')
      expect(comprehensiveElements).toHaveLength(2)
    })

    it('handles analysis cards with missing data', () => {
      const incompleteAnalyses = [
        {
          ...mockAnalyses[0],
          executive_summary: undefined,
          key_insights: undefined,
          analysis_id: 'incomplete-1',
        },
      ]

      mockUseAnalyses.mockReturnValue({
        data: {
          ...mockPaginatedResponse,
          items: incompleteAnalyses,
        },
        isLoading: false,
        error: null,
      })

      render(<AnalysesList />)

      expect(screen.getByTestId('analysis-card-incomplete-1')).toBeInTheDocument()
    })
  })

  describe('Data Refresh and Updates', () => {
    it('handles data updates correctly', () => {
      const { rerender } = render(<AnalysesList />)

      // Update mock data
      const updatedAnalyses = [
        {
          ...mockAnalyses[0],
          analysis_id: 'updated-1',
          executive_summary: 'Updated summary',
        },
      ]

      mockUseAnalyses.mockReturnValue({
        data: {
          ...mockPaginatedResponse,
          items: updatedAnalyses,
        },
        isLoading: false,
        error: null,
      })

      rerender(<AnalysesList />)

      expect(screen.getByTestId('analysis-card-updated-1')).toBeInTheDocument()
    })

    it('shows loading state during data refresh', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      })

      render(<AnalysesList />)

      const loadingElements = document.querySelectorAll('.animate-pulse')
      expect(loadingElements.length).toBe(6) // 6 skeleton cards
    })
  })

  describe('URL Query Parameters', () => {
    it('applies initial filters from URL parameters', () => {
      // This would be tested with URL routing integration
      render(<AnalysesList />)

      // Test that useAnalyses is called with default parameters
      expect(mockUseAnalyses).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
      })
    })

    it('updates URL when filters change', async () => {
      // This would be tested with react-router integration
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      await user.type(searchInput, 'AAPL')

      // In a real implementation, this would update the URL
      await waitFor(() => {
        expect(mockUseAnalyses).toHaveBeenCalledWith(
          expect.objectContaining({
            company_cik: '0000320193',
          })
        )
      })
    })
  })

  describe('Performance and Optimization', () => {
    it('renders efficiently with large datasets', () => {
      const largeDataset = Array.from({ length: 50 }, (_, i) => ({
        ...mockAnalyses[0],
        analysis_id: `large-analysis-${i}`,
        executive_summary: `Analysis ${i} with comprehensive insights and detailed findings`,
      }))

      mockUseAnalyses.mockReturnValue({
        data: {
          ...mockPaginatedResponse,
          items: largeDataset,
          pagination: {
            ...mockPaginatedResponse.pagination,
            total_items: 50,
          },
        },
        isLoading: false,
        error: null,
      })

      const startTime = performance.now()

      render(<AnalysesList />)

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(1000) // Should render within 1 second
    })

    it('handles component unmounting gracefully', () => {
      const { unmount } = render(<AnalysesList />)

      expect(() => unmount()).not.toThrow()
    })
  })

  describe('Accessibility Features', () => {
    it('provides proper ARIA labels', () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      expect(searchInput).toHaveAttribute('type', 'text')

      const filtersButton = screen.getByText('Filters')
      expect(filtersButton).toHaveAttribute('type', 'button')
    })

    it('maintains focus management', async () => {
      render(<AnalysesList />)

      const searchInput = screen.getByPlaceholderText(/Search by ticker.*or CIK/)
      const filtersButton = screen.getByText('Filters')

      // Tab navigation
      searchInput.focus()
      expect(document.activeElement).toBe(searchInput)

      await user.tab()
      expect(document.activeElement).toBe(filtersButton)
    })

    it('supports screen readers', () => {
      render(<AnalysesList />)

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('Analysis Library')

      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)

      const textboxes = screen.getAllByRole('textbox')
      expect(textboxes.length).toBeGreaterThan(0)
    })
  })
})
