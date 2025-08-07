import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import { CompanySearch } from './CompanySearch'
import type { CompanyResponse } from '@/api/types'

// Mock navigate function
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock UI components to focus on business logic
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, disabled, variant, size, className, ...props }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-variant={variant}
      data-size={size}
      className={className}
      data-testid="mock-button"
      {...props}
    >
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/Input', () => ({
  Input: ({ value, onChange, placeholder, className, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={className}
      data-testid="mock-input"
      {...props}
    />
  ),
}))

vi.mock('./components/CompanyCard', () => ({
  CompanyCard: ({ company, onViewProfile, showAnalyses, ticker }: any) => (
    <div data-testid="company-card">
      <span data-testid="company-name">{company?.display_name || 'Loading...'}</span>
      <span data-testid="company-ticker">{ticker || company?.ticker}</span>
      <button
        onClick={() => onViewProfile?.(ticker || company?.ticker)}
        data-testid="view-profile-button"
      >
        View Profile
      </button>
      {showAnalyses && <span data-testid="show-analyses">Show Analyses</span>}
    </div>
  ),
}))

// Test wrapper with React Query and Router
const createTestWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </BrowserRouter>
  )
}

// Mock company data
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
      analysis_id: '1',
      analysis_type: 'COMPREHENSIVE',
      created_at: '2024-01-16T10:00:00Z',
      confidence_score: 0.95,
    },
  ],
}

describe('CompanySearch', () => {
  let TestWrapper: ReturnType<typeof createTestWrapper>
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    vi.clearAllMocks()
    TestWrapper = createTestWrapper()
    user = userEvent.setup()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })
      expect(screen.getByText('Search Companies')).toBeInTheDocument()
    })

    it('renders the search form elements', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      expect(screen.getByRole('heading', { name: 'Search Companies' })).toBeInTheDocument()
      expect(
        screen.getByPlaceholderText('Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)')
      ).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
    })

    it('shows help section by default', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      expect(screen.getByText('How to search')).toBeInTheDocument()
      expect(screen.getByText('Popular examples:')).toBeInTheDocument()
      expect(screen.getByText('AAPL')).toBeInTheDocument()
      expect(screen.getByText('MSFT')).toBeInTheDocument()
    })
  })

  describe('Search Input Handling', () => {
    it('updates search term when typing', async () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      await user.type(input, 'AAPL')

      expect(input).toHaveValue('AAPL')
    })

    it('disables search button when input is empty', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      const searchButton = screen.getByRole('button', { name: /search/i })
      expect(searchButton).toBeDisabled()
    })

    it('enables search button when input has value', async () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      expect(searchButton).not.toBeDisabled()
    })
  })

  describe('Search Form Submission', () => {
    it('performs search when form is submitted', async () => {
      // Mock successful company response
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      expect(screen.getByText(/Searching for:/)).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })
    })

    it('shows loading state during search', async () => {
      // Mock slow response
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', async () => {
          await new Promise((resolve) => setTimeout(resolve, 100))
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      expect(screen.getByText('Searching for company...')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })
    })
  })

  describe('Popular Examples', () => {
    it('renders popular ticker examples', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      const popularTickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META']
      popularTickers.forEach((ticker) => {
        expect(screen.getByText(ticker)).toBeInTheDocument()
      })
    })

    it('searches when popular example is clicked', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const appleButton = screen.getByRole('button', { name: 'AAPL' })
      await user.click(appleButton)

      expect(screen.getByText(/Searching for:/)).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })
    })
  })

  describe('Search Results', () => {
    it('displays search results when company is found', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Search Results')).toBeInTheDocument()
        expect(screen.getByText('1 company found')).toBeInTheDocument()
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })
    })

    it('shows error message when company is not found', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/INVALID', () => {
          return HttpResponse.json(
            { detail: 'Company not found', status_code: 404 },
            { status: 404 }
          )
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'INVALID')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Company not found')).toBeInTheDocument()
        expect(screen.getByText(/Could not find a company with ticker/)).toBeInTheDocument()
      })
    })

    it('provides retry functionality on error', async () => {
      let callCount = 0
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          callCount++
          if (callCount === 1) {
            return HttpResponse.json({ detail: 'Server error', status_code: 500 }, { status: 500 })
          }
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Company not found')).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: 'Try Again' })
      await user.click(retryButton)

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })
    })
  })

  describe('Clear Search', () => {
    it('clears search results and input', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })

      const clearButton = screen.getByRole('button', { name: 'Clear' })
      await user.click(clearButton)

      expect(input).toHaveValue('')
      expect(screen.queryByTestId('company-card')).not.toBeInTheDocument()
      expect(screen.getByText('How to search')).toBeInTheDocument()
    })
  })

  describe('Company Selection', () => {
    it('navigates to company profile by default', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })

      const viewProfileButton = screen.getByTestId('view-profile-button')
      await user.click(viewProfileButton)

      expect(mockNavigate).toHaveBeenCalledWith('/companies/AAPL')
    })

    it('calls onCompanySelect callback when provided', async () => {
      const mockOnCompanySelect = vi.fn()

      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch onCompanySelect={mockOnCompanySelect} />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByTestId('company-card')).toBeInTheDocument()
      })

      const viewProfileButton = screen.getByTestId('view-profile-button')
      await user.click(viewProfileButton)

      expect(mockOnCompanySelect).toHaveBeenCalledWith('AAPL')
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })

  describe('Props and Options', () => {
    it('passes showAnalyses prop to CompanyCard', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/AAPL', () => {
          return HttpResponse.json(mockCompany)
        })
      )

      render(<CompanySearch showAnalyses={true} />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'AAPL')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByTestId('show-analyses')).toBeInTheDocument()
      })
    })

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>()

      render(<CompanySearch ref={ref} />, { wrapper: TestWrapper })

      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML structure', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
      expect(screen.getByTestId('mock-input')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
    })

    it('provides descriptive text for search functionality', () => {
      render(<CompanySearch />, { wrapper: TestWrapper })

      expect(
        screen.getByText(
          'Enter a company ticker symbol to search for company information and analysis'
        )
      ).toBeInTheDocument()
    })

    it('shows clear error messages', async () => {
      server.use(
        http.get('http://localhost:8000/api/companies/INVALID', () => {
          return HttpResponse.json(
            { detail: 'Company not found', status_code: 404 },
            { status: 404 }
          )
        })
      )

      render(<CompanySearch />, { wrapper: TestWrapper })

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByRole('button', { name: /search/i })

      await user.type(input, 'INVALID')
      await user.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText('Company not found')).toBeInTheDocument()
        expect(
          screen.getByText(
            'Could not find a company with ticker "INVALID". Please check the spelling and try again.'
          )
        ).toBeInTheDocument()
      })
    })
  })
})
