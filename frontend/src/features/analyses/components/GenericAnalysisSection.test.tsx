import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { GenericAnalysisSection } from './GenericAnalysisSection'

// Mock the sub-components
vi.mock('./FinancialMetricsGrid', () => ({
  FinancialMetricsGrid: vi.fn(() => <div data-testid="financial-metrics-grid">Financial Metrics Grid</div>)
}))

vi.mock('./RiskFactorCard', () => ({
  RiskFactorList: vi.fn(() => <div data-testid="risk-factor-list">Risk Factor List</div>),
  RiskFactorCard: vi.fn(() => <div data-testid="risk-factor-card">Risk Factor Card</div>)
}))

vi.mock('./EnhancedSectionHeader', () => ({
  EnhancedSectionHeader: vi.fn(({ title, onToggle, isExpanded }) => (
    <div data-testid="enhanced-section-header">
      <h3>{title}</h3>
      <button onClick={onToggle} data-testid="toggle-button">
        {isExpanded ? 'Collapse' : 'Expand'}
      </button>
    </div>
  )),
  getAnalysisType: vi.fn(() => 'financial'),
  extractSectionMetadata: vi.fn(() => ({ confidence: 0.85, totalItems: 5 }))
}))

vi.mock('@/components/ui/Button', () => ({
  Button: vi.fn(({ children, onClick, className, ...props }) => (
    <button onClick={onClick} className={className} {...props}>
      {children}
    </button>
  ))
}))

describe('GenericAnalysisSection', () => {
  // Props that will trigger specialized rendering (for specialized tests)
  const specializedProps = {
    analysis: {
      executive_summary: 'Test executive summary',
      key_financial_metrics: [
        { metric_name: 'Revenue', current_value: 1000, previous_value: 900 },
        { metric_name: 'Profit', current_value: 200, previous_value: 150 }
      ],
      risk_factors: [
        { risk_name: 'Market Risk', description: 'Test risk description' }
      ],
      business_strategy: 'Test business strategy',
      other_field: 'Test other field'
    },
    schemaType: 'TestAnalysisSchema'
  }

  // Props that will NOT trigger specialized rendering (for generic tests)
  const genericProps = {
    analysis: {
      general_summary: 'Test general summary',
      company_overview: 'Test company overview', 
      market_position: 'Strong market position',
      competitive_landscape: 'Competitive market',
      growth_outlook: 'Positive growth expected',
      conclusion: 'Overall positive analysis'
    },
    schemaType: 'GeneralAnalysisSchema'
  }

  describe('Loading State', () => {
    it('should display loading skeleton when loading prop is true', () => {
      render(<GenericAnalysisSection {...genericProps} loading={true} />)
      
      // Find loading container using class selector
      const loadingElement = document.querySelector('.animate-pulse')
      expect(loadingElement).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('should display error message for invalid analysis data', () => {
      render(<GenericAnalysisSection analysis={null} schemaType="TestSchema" />)
      
      expect(screen.getByText('Invalid Analysis Data')).toBeInTheDocument()
      expect(screen.getByText(/Unable to display analysis for schema type: TestSchema/)).toBeInTheDocument()
    })

    it('should display error message for non-object analysis', () => {
      render(<GenericAnalysisSection analysis="invalid" schemaType="TestSchema" />)
      
      expect(screen.getByText('Invalid Analysis Data')).toBeInTheDocument()
    })
  })

  describe('Specialized Content Rendering', () => {
    it('should render FinancialMetricsGrid for financial metrics', () => {
      const analysisWithMetrics = {
        metric_name: 'Revenue',
        current_value: 1000,
        previous_value: 900
      }

      render(<GenericAnalysisSection analysis={analysisWithMetrics} schemaType="FinancialMetric" />)
      
      expect(screen.getByTestId('financial-metrics-grid')).toBeInTheDocument()
    })

    it('should render RiskFactorList for risk factors array', () => {
      const analysisWithRisks = [
        { risk_name: 'Market Risk', description: 'Test risk' }
      ]

      render(<GenericAnalysisSection analysis={analysisWithRisks} schemaType="RiskFactors" />)
      
      expect(screen.getByTestId('risk-factor-list')).toBeInTheDocument()
    })

    it('should render nested financial metrics', () => {
      render(<GenericAnalysisSection {...specializedProps} />)
      
      expect(screen.getByTestId('financial-metrics-grid')).toBeInTheDocument()
    })
  })

  describe('Generic Content Rendering', () => {
    it('should render enhanced section header', () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      expect(screen.getByTestId('enhanced-section-header')).toBeInTheDocument()
      expect(screen.getByText('General Analysis Schema')).toBeInTheDocument()
    })

    it('should handle expand/collapse functionality', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const toggleButton = screen.getByTestId('toggle-button')
      
      // Should be expanded by default
      expect(screen.getByText('Collapse')).toBeInTheDocument()
      
      fireEvent.click(toggleButton)
      
      await waitFor(() => {
        expect(screen.getByText('Expand')).toBeInTheDocument()
      })
    })

    it('should display content categories when data has multiple items', () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      // Should show category tabs for complex data
      expect(screen.getByText(/All \(\d+\)/)).toBeInTheDocument()
    })

    it('should handle search functionality', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const searchInput = screen.getByPlaceholderText('Search analysis content...')
      
      fireEvent.change(searchInput, { target: { value: 'general' } })
      
      await waitFor(() => {
        expect(searchInput.value).toBe('general')
      })
    })
  })

  describe('Content Categorization', () => {
    it('should categorize financial content correctly', () => {
      const financialAnalysis = {
        revenue_growth: '15%',
        profit_margin: '12%',
        financial_highlights: ['Strong revenue growth']
      }

      render(<GenericAnalysisSection analysis={financialAnalysis} schemaType="FinancialAnalysis" />)
      
      // Should show financial badges on content items (multiple instances expected)
      expect(screen.getAllByText('Financial').length).toBeGreaterThan(0)
      expect(screen.getByText('Revenue Growth')).toBeInTheDocument()
    })

    it('should categorize risk content correctly', () => {
      const riskAnalysis = {
        market_risks: ['Competition risk'],
        risk_assessment: 'High risk scenario',
        threats_identified: ['Market volatility']
      }

      render(<GenericAnalysisSection analysis={riskAnalysis} schemaType="RiskAnalysis" />)
      
      // Should show risks badges on content items (multiple instances expected)
      expect(screen.getAllByText('Risks').length).toBeGreaterThan(0)
      expect(screen.getByText('Market Risks')).toBeInTheDocument()
    })

    it('should categorize business content correctly', () => {
      const businessAnalysis = {
        business_model: 'SaaS platform',
        market_strategy: 'Growth focused',
        competitive_advantage: 'First mover advantage'
      }

      render(<GenericAnalysisSection analysis={businessAnalysis} schemaType="BusinessAnalysis" />)
      
      // Should show business badges on content items (multiple instances expected)
      expect(screen.getAllByText('Business').length).toBeGreaterThan(0)
      expect(screen.getByText('Business Model')).toBeInTheDocument()
    })
  })

  describe('Filter Functionality', () => {
    it('should show filter controls when filters are enabled', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const filtersButton = screen.getByText('Filters')
      fireEvent.click(filtersButton)
      
      await waitFor(() => {
        expect(screen.getByText('Show:')).toBeInTheDocument()
        expect(screen.getByText('Key Items')).toBeInTheDocument()
      })
    })

    it('should handle filter changes', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const filtersButton = screen.getByText('Filters')
      fireEvent.click(filtersButton)
      
      await waitFor(() => {
        const keyItemsFilter = screen.getByText('Key Items')
        fireEvent.click(keyItemsFilter)
      })
      
      // Should filter to significant items only
    })
  })

  describe('Empty States', () => {
    it('should show empty state when no content matches filters', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const searchInput = screen.getByPlaceholderText('Search analysis content...')
      fireEvent.change(searchInput, { target: { value: 'nonexistentcontent' } })
      
      await waitFor(() => {
        expect(screen.getByText('No Content Found')).toBeInTheDocument()
        expect(screen.getByText(/No analysis content matches your search criteria/)).toBeInTheDocument()
      })
    })

    it('should provide clear search button in empty state', async () => {
      render(<GenericAnalysisSection {...genericProps} />)
      
      const searchInput = screen.getByPlaceholderText('Search analysis content...')
      fireEvent.change(searchInput, { target: { value: 'nonexistentcontent' } })
      
      await waitFor(() => {
        expect(screen.getByText('Clear Search')).toBeInTheDocument()
      })
    })
  })

  describe('Value Rendering', () => {
    it('should handle different value types correctly', () => {
      const mixedAnalysis = {
        string_value: 'Test string',
        number_value: 42,
        boolean_value: true,
        null_value: null,
        array_value: ['item1', 'item2'],
        object_value: { nested: 'value' }
      }

      render(<GenericAnalysisSection analysis={mixedAnalysis} schemaType="MixedAnalysis" />)
      
      // Should handle all value types without errors
      expect(screen.getByTestId('enhanced-section-header')).toBeInTheDocument()
    })

    it('should truncate long string values', () => {
      const longStringAnalysis = {
        long_description: 'A'.repeat(400) // Very long string
      }

      render(<GenericAnalysisSection analysis={longStringAnalysis} schemaType="LongContent" />)
      
      // Should show "Show more" button for long content
      expect(screen.getByText(/Show more/)).toBeInTheDocument()
    })
  })

  describe('Development Debug Info', () => {
    it('should show debug info in development mode', () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'development'
      
      render(<GenericAnalysisSection {...genericProps} />)
      
      expect(screen.getByText(/Debug: Schema & Processing Info/)).toBeInTheDocument()
      
      process.env.NODE_ENV = originalEnv
    })
  })
})