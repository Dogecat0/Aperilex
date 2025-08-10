import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CompanyCard } from './CompanyCard'
import type { CompanyResponse } from '@/api/types'

// Mock UI components to focus on business logic
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, variant, size, className, ...props }: any) => (
    <button
      onClick={onClick}
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
      analysis_template: 'comprehensive',
      created_at: '2024-01-16T10:00:00Z',
      confidence_score: 0.95,
    },
    {
      analysis_id: '2',
      analysis_template: 'financial_focused',
      created_at: '2024-01-15T10:00:00Z',
      confidence_score: 0.88,
    },
    {
      analysis_id: '3',
      analysis_template: 'risk_focused',
      created_at: '2024-01-14T10:00:00Z',
      confidence_score: 0.92,
    },
  ],
}

const mockCompanyNoTicker: CompanyResponse = {
  ...mockCompany,
  ticker: null,
}

const mockCompanyMinimal: CompanyResponse = {
  company_id: '123456',
  ticker: 'TEST',
  name: 'Test Company',
  display_name: 'Test Company',
  cik: '0001234567',
  sic_code: null,
  sic_description: null,
  industry: null,
  fiscal_year_end: null,
  business_address: null,
}

describe('CompanyCard', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    vi.clearAllMocks()
    user = userEvent.setup()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<CompanyCard company={mockCompany} />)
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('applies correct card styling classes', () => {
      const { container } = render(<CompanyCard company={mockCompany} />)
      const card = container.firstChild as HTMLElement

      expect(card).toHaveClass(
        'rounded-lg',
        'border',
        'bg-card',
        'p-6',
        'space-y-4',
        'hover:shadow-md',
        'transition-shadow'
      )
    })

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>()

      render(<CompanyCard company={mockCompany} ref={ref} />)

      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('Company Information Display', () => {
    it('displays company name correctly', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      expect(screen.getByText('Apple Inc.')).toHaveClass(
        'text-lg',
        'font-semibold',
        'text-foreground'
      )
    })

    it('displays ticker symbol when available', () => {
      render(<CompanyCard company={mockCompany} />)

      const tickerElement = screen.getByText('AAPL')
      expect(tickerElement).toBeInTheDocument()
      expect(tickerElement).toHaveClass(
        'inline-flex',
        'items-center',
        'px-2',
        'py-1',
        'rounded-md',
        'bg-secondary',
        'text-secondary-foreground',
        'text-sm',
        'font-medium'
      )
    })

    it('uses explicit ticker prop when company ticker is null', () => {
      render(<CompanyCard company={mockCompanyNoTicker} ticker="EXPLICIT" />)

      expect(screen.getByText('EXPLICIT')).toBeInTheDocument()
    })

    it('displays industry when available', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.getByText('Technology')).toBeInTheDocument()
    })

    it('displays CIK number', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.getByText('CIK: 0000320193')).toBeInTheDocument()
    })

    it('displays fiscal year end when available', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.getByText('Fiscal Year End: 09-30')).toBeInTheDocument()
    })
  })

  describe('Business Address Display', () => {
    it('displays complete business address', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.getByText('Cupertino, CA, US')).toBeInTheDocument()
    })

    it('handles partial address information', () => {
      const companyPartialAddress: CompanyResponse = {
        ...mockCompany,
        business_address: {
          city: 'Cupertino',
          state: 'CA',
          country: null,
        },
      }

      render(<CompanyCard company={companyPartialAddress} />)

      expect(screen.getByText('Cupertino, CA')).toBeInTheDocument()
    })

    it('handles missing address', () => {
      render(<CompanyCard company={mockCompanyMinimal} />)

      // Should not show address section at all
      expect(screen.queryByText(/,/)).not.toBeInTheDocument()
    })
  })

  describe('View Profile Button', () => {
    it('renders view profile button when onViewProfile and ticker provided', () => {
      const mockOnViewProfile = vi.fn()

      render(<CompanyCard company={mockCompany} onViewProfile={mockOnViewProfile} />)

      expect(screen.getByText('View Profile')).toBeInTheDocument()
    })

    it('calls onViewProfile with ticker when button clicked', async () => {
      const mockOnViewProfile = vi.fn()

      render(<CompanyCard company={mockCompany} onViewProfile={mockOnViewProfile} />)

      const viewButton = screen.getByText('View Profile')
      await user.click(viewButton)

      expect(mockOnViewProfile).toHaveBeenCalledWith('AAPL')
    })

    it('uses explicit ticker prop for callback', async () => {
      const mockOnViewProfile = vi.fn()

      render(
        <CompanyCard
          company={mockCompanyNoTicker}
          onViewProfile={mockOnViewProfile}
          ticker="EXPLICIT"
        />
      )

      const viewButton = screen.getByText('View Profile')
      await user.click(viewButton)

      expect(mockOnViewProfile).toHaveBeenCalledWith('EXPLICIT')
    })

    it('does not render view profile button when no ticker available', () => {
      const mockOnViewProfile = vi.fn()

      render(<CompanyCard company={mockCompanyNoTicker} onViewProfile={mockOnViewProfile} />)

      expect(screen.queryByText('View Profile')).not.toBeInTheDocument()
    })

    it('does not render view profile button when no onViewProfile callback', () => {
      render(<CompanyCard company={mockCompany} />)

      expect(screen.queryByText('View Profile')).not.toBeInTheDocument()
    })
  })

  describe('Recent Analyses Section', () => {
    it('shows recent analyses when showAnalyses is true and analyses exist', () => {
      render(<CompanyCard company={mockCompany} showAnalyses={true} />)

      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
      expect(screen.getByText('comprehensive')).toBeInTheDocument()
      expect(screen.getByText('financial_focused')).toBeInTheDocument()
      expect(screen.getByText('risk_focused')).toBeInTheDocument()
    })

    it('limits recent analyses display to first 3', () => {
      const companyManyAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [
          ...mockCompany.recent_analyses!,
          {
            analysis_id: '4',
            analysis_template: 'business_focused',
            created_at: '2024-01-13T10:00:00Z',
            confidence_score: 0.85,
          },
          {
            analysis_id: '5',
            analysis_template: 'comprehensive',
            created_at: '2024-01-12T10:00:00Z',
            confidence_score: 0.9,
          },
        ],
      }

      render(<CompanyCard company={companyManyAnalyses} showAnalyses={true} />)

      // Should only show first 3 analyses
      expect(screen.getByText('comprehensive')).toBeInTheDocument()
      expect(screen.getByText('financial_focused')).toBeInTheDocument()
      expect(screen.getByText('risk_focused')).toBeInTheDocument()
      expect(screen.queryByText('business_focused')).not.toBeInTheDocument()
    })

    it('shows analysis dates correctly formatted', () => {
      render(<CompanyCard company={mockCompany} showAnalyses={true} />)

      // Should show formatted dates (testing the date formatting)
      const dateElements = screen.getAllByText(/\d{1,2}\/\d{1,2}\/\d{4}/)
      expect(dateElements).toHaveLength(3) // One for each analysis
    })

    it('does not show analyses section when showAnalyses is false', () => {
      render(<CompanyCard company={mockCompany} showAnalyses={false} />)

      expect(screen.queryByText('Recent Analyses')).not.toBeInTheDocument()
    })

    it('does not show analyses section when no analyses exist', () => {
      const companyNoAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [],
      }

      render(<CompanyCard company={companyNoAnalyses} showAnalyses={true} />)

      expect(screen.queryByText('Recent Analyses')).not.toBeInTheDocument()
    })

    it('handles undefined recent_analyses array', () => {
      const companyNoAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: undefined,
      }

      render(<CompanyCard company={companyNoAnalyses} showAnalyses={true} />)

      expect(screen.queryByText('Recent Analyses')).not.toBeInTheDocument()
    })
  })

  describe('Minimal Company Data', () => {
    it('handles company with minimal required fields', () => {
      render(<CompanyCard company={mockCompanyMinimal} />)

      expect(screen.getByText('Test Company')).toBeInTheDocument()
      expect(screen.getByText('TEST')).toBeInTheDocument()
      expect(screen.getByText('CIK: 0001234567')).toBeInTheDocument()

      // Should not show optional fields
      expect(screen.queryByText('Technology')).not.toBeInTheDocument()
      expect(screen.queryByText('Fiscal Year End:')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic structure', () => {
      render(<CompanyCard company={mockCompany} />)

      // Company name should be in a heading
      const heading = screen.getByText('Apple Inc.')
      expect(heading).toHaveClass('text-lg', 'font-semibold')
    })

    it('provides meaningful text content for screen readers', () => {
      render(<CompanyCard company={mockCompany} showAnalyses={true} />)

      // All important information should be in text content
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      expect(screen.getByText('AAPL')).toBeInTheDocument()
      expect(screen.getByText('Technology')).toBeInTheDocument()
      expect(screen.getByText('CIK: 0000320193')).toBeInTheDocument()
    })

    it('maintains proper button accessibility', async () => {
      const mockOnViewProfile = vi.fn()

      render(<CompanyCard company={mockCompany} onViewProfile={mockOnViewProfile} />)

      const button = screen.getByText('View Profile')
      expect(button.tagName).toBe('BUTTON')
      expect(button).not.toBeDisabled()
    })
  })

  describe('Visual Indicators', () => {
    it('renders building icon for company', () => {
      const { container } = render(<CompanyCard company={mockCompany} />)

      // Check for Building icon (lucide-react building icon)
      const buildingIcon = container.querySelector('svg')
      expect(buildingIcon).toBeInTheDocument()
    })

    it('renders appropriate icons for different data types', () => {
      const { container } = render(<CompanyCard company={mockCompany} />)

      // Should have multiple icons for different sections
      const svgElements = container.querySelectorAll('svg')
      expect(svgElements.length).toBeGreaterThan(1) // Building, BarChart3, MapPin, Calendar icons
    })

    it('shows primary indicator dots for recent analyses', () => {
      render(<CompanyCard company={mockCompany} showAnalyses={true} />)

      const { container } = render(<CompanyCard company={mockCompany} showAnalyses={true} />)

      // Should have dot indicators for each analysis
      const dotElements = container.querySelectorAll('.w-2.h-2.bg-primary.rounded-full')
      expect(dotElements.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('Hover Effects', () => {
    it('applies hover shadow effect', () => {
      const { container } = render(<CompanyCard company={mockCompany} />)
      const card = container.firstChild as HTMLElement

      expect(card).toHaveClass('hover:shadow-md', 'transition-shadow')
    })
  })

  describe('Layout and Spacing', () => {
    it('maintains proper spacing between sections', () => {
      const { container } = render(<CompanyCard company={mockCompany} showAnalyses={true} />)
      const card = container.firstChild as HTMLElement

      expect(card).toHaveClass('space-y-4')
    })

    it('applies proper border and background styling', () => {
      const { container } = render(<CompanyCard company={mockCompany} />)
      const card = container.firstChild as HTMLElement

      expect(card).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })
  })
})
