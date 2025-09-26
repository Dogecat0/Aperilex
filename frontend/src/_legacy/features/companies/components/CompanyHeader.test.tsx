import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CompanyHeader } from './CompanyHeader'
import type { CompanyResponse } from '@/api/types'

// Mock UI components to focus on business logic
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, variant, className, ...props }: any) => (
    <button
      onClick={onClick}
      data-variant={variant}
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
  ],
}

const mockCompanyMinimal: CompanyResponse = {
  company_id: '123456',
  ticker: null,
  name: 'Test Company',
  display_name: 'Test Company',
  cik: '0001234567',
  sic_code: null,
  sic_description: null,
  industry: null,
  fiscal_year_end: null,
  business_address: null,
}

describe('CompanyHeader', () => {
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
      render(<CompanyHeader company={mockCompany} />)
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('applies correct card styling', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)
      const header = container.firstChild as HTMLElement

      expect(header).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>()

      render(<CompanyHeader company={mockCompany} ref={ref} />)

      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('Company Information Display', () => {
    it('displays company name as main heading', () => {
      render(<CompanyHeader company={mockCompany} />)

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('Apple Inc.')
      expect(heading).toHaveClass('text-2xl', 'font-bold', 'text-foreground')
    })

    it('displays ticker symbol when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      const tickerElement = screen.getByText('AAPL')
      expect(tickerElement).toBeInTheDocument()
      expect(tickerElement).toHaveClass(
        'inline-flex',
        'items-center',
        'px-3',
        'py-1',
        'mt-1',
        'rounded-md',
        'bg-primary',
        'text-primary-foreground',
        'text-sm',
        'font-semibold'
      )
    })

    it('handles company without ticker', () => {
      render(<CompanyHeader company={mockCompanyMinimal} />)

      expect(screen.queryByText('AAPL')).not.toBeInTheDocument()
      expect(screen.getByText('Test Company')).toBeInTheDocument()
    })

    it('displays industry when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('Industry')).toBeInTheDocument()
      expect(screen.getByText('Technology')).toBeInTheDocument()
    })

    it('displays CIK number', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('CIK')).toBeInTheDocument()
      expect(screen.getByText('0000320193')).toBeInTheDocument()
    })

    it('displays fiscal year end when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('Fiscal Year End')).toBeInTheDocument()
      expect(screen.getByText('09-30')).toBeInTheDocument()
    })
  })

  describe('Business Address Display', () => {
    it('displays complete business address', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('Location')).toBeInTheDocument()
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

      render(<CompanyHeader company={companyPartialAddress} />)

      expect(screen.getByText('Cupertino, CA')).toBeInTheDocument()
    })

    it('does not show location when address is missing', () => {
      render(<CompanyHeader company={mockCompanyMinimal} />)

      expect(screen.queryByText('Location')).not.toBeInTheDocument()
    })
  })

  describe('SIC Information Display', () => {
    it('displays SIC code and description when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('SIC Classification')).toBeInTheDocument()
      expect(screen.getByText('3571 - Electronic Computers')).toBeInTheDocument()
    })

    it('displays only SIC description when code is missing', () => {
      const companySicDescOnly: CompanyResponse = {
        ...mockCompany,
        sic_code: null,
        sic_description: 'Electronic Computers',
      }

      render(<CompanyHeader company={companySicDescOnly} />)

      expect(screen.getByText('Electronic Computers')).toBeInTheDocument()
    })

    it('does not show SIC section when both code and description are missing', () => {
      render(<CompanyHeader company={mockCompanyMinimal} />)

      expect(screen.queryByText('SIC Classification')).not.toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('renders analyze filings button when callback provided', () => {
      const mockOnAnalyzeFilings = vi.fn()

      render(<CompanyHeader company={mockCompany} onAnalyzeFilings={mockOnAnalyzeFilings} />)

      expect(screen.getByText('Analyze Filings')).toBeInTheDocument()
    })

    it('renders view analyses button when callback provided', () => {
      const mockOnViewAnalyses = vi.fn()

      render(<CompanyHeader company={mockCompany} onViewAnalyses={mockOnViewAnalyses} />)

      expect(screen.getByText('View All Analyses')).toBeInTheDocument()
    })

    it('calls onAnalyzeFilings when button clicked', async () => {
      const mockOnAnalyzeFilings = vi.fn()

      render(<CompanyHeader company={mockCompany} onAnalyzeFilings={mockOnAnalyzeFilings} />)

      const analyzeButton = screen.getByText('Analyze Filings')
      await user.click(analyzeButton)

      expect(mockOnAnalyzeFilings).toHaveBeenCalledTimes(1)
    })

    it('calls onViewAnalyses when button clicked', async () => {
      const mockOnViewAnalyses = vi.fn()

      render(<CompanyHeader company={mockCompany} onViewAnalyses={mockOnViewAnalyses} />)

      const viewAnalysesButton = screen.getByText('View All Analyses')
      await user.click(viewAnalysesButton)

      expect(mockOnViewAnalyses).toHaveBeenCalledTimes(1)
    })

    it('does not render buttons when no callbacks provided', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.queryByText('Analyze Filings')).not.toBeInTheDocument()
      expect(screen.queryByText('View All Analyses')).not.toBeInTheDocument()
    })

    it('applies correct button variants', () => {
      const mockOnAnalyzeFilings = vi.fn()
      const mockOnViewAnalyses = vi.fn()

      render(
        <CompanyHeader
          company={mockCompany}
          onAnalyzeFilings={mockOnAnalyzeFilings}
          onViewAnalyses={mockOnViewAnalyses}
        />
      )

      const analyzeButton = screen.getByText('Analyze Filings')
      const viewAnalysesButton = screen.getByText('View All Analyses')

      // Primary button (no variant attribute)
      expect(analyzeButton).not.toHaveAttribute('data-variant')
      // Outline button
      expect(viewAnalysesButton).toHaveAttribute('data-variant', 'outline')
    })
  })

  describe('Recent Activity Section', () => {
    it('displays recent analyses when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('Recent Activity')).toBeInTheDocument()
      const analysisElements = screen.getAllByText((content, element) => {
        return /2\s*recent\s*analys(is|es)/.test(element?.textContent || '')
      })
      expect(analysisElements.length).toBeGreaterThan(0)
    })

    it('shows individual analysis cards', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('comprehensive')).toBeInTheDocument()
      expect(screen.getByText('financial_focused')).toBeInTheDocument()
    })

    it('displays confidence scores when available', () => {
      render(<CompanyHeader company={mockCompany} />)

      expect(screen.getByText('Confidence: 95%')).toBeInTheDocument()
      expect(screen.getByText('Confidence: 88%')).toBeInTheDocument()
    })

    it('formats analysis dates correctly', () => {
      render(<CompanyHeader company={mockCompany} />)

      // Should show formatted dates
      const dateElements = screen.getAllByText(/\d{1,2}\/\d{1,2}\/\d{4}/)
      expect(dateElements).toHaveLength(2) // One for each analysis
    })

    it('limits display to first 3 analyses', () => {
      const companyManyAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [
          ...mockCompany.recent_analyses!,
          {
            analysis_id: '3',
            analysis_template: 'risk_focused',
            created_at: '2024-01-14T10:00:00Z',
            confidence_score: 0.92,
          },
          {
            analysis_id: '4',
            analysis_template: 'business_focused',
            created_at: '2024-01-13T10:00:00Z',
            confidence_score: 0.85,
          },
        ],
      }

      render(<CompanyHeader company={companyManyAnalyses} />)

      expect(screen.getByText('comprehensive')).toBeInTheDocument()
      expect(screen.getByText('financial_focused')).toBeInTheDocument()
      expect(screen.getByText('risk_focused')).toBeInTheDocument()
      expect(screen.queryByText('business_focused')).not.toBeInTheDocument()
    })

    it('uses correct singular/plural for analyses count', () => {
      const companySingleAnalysis: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [mockCompany.recent_analyses![0]],
      }

      render(<CompanyHeader company={companySingleAnalysis} />)

      expect(screen.getByText('1 recent analysis')).toBeInTheDocument()
    })

    it('does not show recent activity when no analyses exist', () => {
      const companyNoAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [],
      }

      render(<CompanyHeader company={companyNoAnalyses} />)

      expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
    })

    it('handles undefined recent_analyses array', () => {
      const companyNoAnalyses: CompanyResponse = {
        ...mockCompany,
        recent_analyses: undefined,
      }

      render(<CompanyHeader company={companyNoAnalyses} />)

      expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
    })
  })

  describe('Layout and Responsive Design', () => {
    it('uses correct responsive flex layout', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      const mainContainer = container.querySelector('.flex.flex-col.lg\\:flex-row')
      expect(mainContainer).toBeInTheDocument()
      expect(mainContainer).toHaveClass(
        'flex',
        'flex-col',
        'lg:flex-row',
        'lg:items-start',
        'lg:justify-between',
        'space-y-4',
        'lg:space-y-0'
      )
    })

    it('displays company details in responsive grid', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      const detailsGrid = container.querySelector('.grid.grid-cols-1.md\\:grid-cols-2')
      expect(detailsGrid).toBeInTheDocument()
      expect(detailsGrid).toHaveClass('grid', 'grid-cols-1', 'md:grid-cols-2', 'gap-4')
    })

    it('displays recent analyses in responsive grid', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      const analysesGrid = container.querySelector(
        '.grid.grid-cols-1.sm\\:grid-cols-2.lg\\:grid-cols-3'
      )
      expect(analysesGrid).toBeInTheDocument()
      expect(analysesGrid).toHaveClass(
        'grid',
        'grid-cols-1',
        'sm:grid-cols-2',
        'lg:grid-cols-3',
        'gap-3'
      )
    })

    it('applies correct responsive button layout', () => {
      const mockOnAnalyzeFilings = vi.fn()
      const mockOnViewAnalyses = vi.fn()

      const { container } = render(
        <CompanyHeader
          company={mockCompany}
          onAnalyzeFilings={mockOnAnalyzeFilings}
          onViewAnalyses={mockOnViewAnalyses}
        />
      )

      const buttonContainer = container.querySelector('.flex.flex-col.sm\\:flex-row.lg\\:flex-col')
      expect(buttonContainer).toBeInTheDocument()
      expect(buttonContainer).toHaveClass(
        'flex',
        'flex-col',
        'sm:flex-row',
        'lg:flex-col',
        'space-y-2',
        'sm:space-y-0',
        'sm:space-x-2',
        'lg:space-x-0',
        'lg:space-y-2'
      )
    })
  })

  describe('Visual Elements', () => {
    it('renders building icon in header', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      // Should have building icon
      const svgElements = container.querySelectorAll('svg')
      expect(svgElements.length).toBeGreaterThan(0)
    })

    it('renders appropriate icons for different data types', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      // Should have multiple icons (Building, BarChart3, MapPin, Calendar, ExternalLink)
      const svgElements = container.querySelectorAll('svg')
      expect(svgElements.length).toBeGreaterThanOrEqual(5)
    })

    it('shows primary indicators for recent analyses', () => {
      const { container } = render(<CompanyHeader company={mockCompany} />)

      // Should have indicator dots for analyses
      const dotElements = container.querySelectorAll('.w-2.h-2.bg-primary.rounded-full')
      expect(dotElements.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML structure', () => {
      render(<CompanyHeader company={mockCompany} />)

      // Main heading
      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('Apple Inc.')

      // Section heading for recent activity
      const activityHeading = screen.getByRole('heading', { level: 3 })
      expect(activityHeading).toHaveTextContent('Recent Activity')
    })

    it('provides accessible button elements', () => {
      const mockOnAnalyzeFilings = vi.fn()
      const mockOnViewAnalyses = vi.fn()

      render(
        <CompanyHeader
          company={mockCompany}
          onAnalyzeFilings={mockOnAnalyzeFilings}
          onViewAnalyses={mockOnViewAnalyses}
        />
      )

      const buttons = screen.getAllByRole('button')
      expect(buttons).toHaveLength(2)

      buttons.forEach((button) => {
        expect(button).not.toBeDisabled()
        expect(button.tagName).toBe('BUTTON')
      })
    })

    it('provides meaningful text descriptions', () => {
      render(<CompanyHeader company={mockCompany} />)

      // Should have descriptive labels for data sections
      expect(screen.getByText('Industry')).toBeInTheDocument()
      expect(screen.getByText('Location')).toBeInTheDocument()
      expect(screen.getByText('Fiscal Year End')).toBeInTheDocument()
      expect(screen.getByText('CIK')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing confidence scores gracefully', () => {
      const companyNoConfidence: CompanyResponse = {
        ...mockCompany,
        recent_analyses: [
          {
            analysis_id: '1',
            analysis_template: 'comprehensive',
            created_at: '2024-01-16T10:00:00Z',
            confidence_score: undefined,
          },
        ],
      }

      render(<CompanyHeader company={companyNoConfidence} />)

      expect(screen.getByText('comprehensive')).toBeInTheDocument()
      expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument()
    })

    it('handles all optional fields missing gracefully', () => {
      render(<CompanyHeader company={mockCompanyMinimal} />)

      // Should still render without errors
      expect(screen.getByText('Test Company')).toBeInTheDocument()
      expect(screen.getByText('CIK')).toBeInTheDocument()
      expect(screen.getByText('0001234567')).toBeInTheDocument()

      // Optional sections should not appear
      expect(screen.queryByText('Industry')).not.toBeInTheDocument()
      expect(screen.queryByText('Location')).not.toBeInTheDocument()
      expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
    })
  })
})
