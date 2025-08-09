import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { AnalysisCard } from './AnalysisCard'
import type { AnalysisResponse } from '@/api/types'

// Mock child components
vi.mock('./ConfidenceIndicator', () => ({
  ConfidenceIndicator: ({ score, size }: { score?: number; size?: string }) => (
    <div data-testid="confidence-indicator" data-score={score} data-size={size}>
      Confidence: {score ? `${Math.round(score * 100)}%` : 'N/A'}
    </div>
  ),
}))

// Mock data for different analysis types
const baseAnalysis: Omit<AnalysisResponse, 'analysis_type'> = {
  analysis_id: 'analysis-123',
  filing_id: 'filing-456',
  created_by: 'user@example.com',
  created_at: '2024-01-15T10:00:00Z',
  confidence_score: 0.88,
  llm_provider: 'openai',
  llm_model: 'gpt-4',
  processing_time_seconds: 32,
  filing_summary: 'Test filing summary',
  executive_summary:
    "This analysis provides comprehensive insights into the company's financial performance and strategic direction.",
  key_insights: [
    'Revenue growth of 15% year-over-year',
    'Strong cash position with $50B in reserves',
    'Market expansion into emerging economies',
  ],
  financial_highlights: ['Revenue up 15%'],
  risk_factors: ['Market volatility'],
  opportunities: ['Emerging markets'],
  sections_analyzed: 5,
  full_results: null,
}

const comprehensiveAnalysis: AnalysisResponse = {
  ...baseAnalysis,
  analysis_type: 'COMPREHENSIVE',
}

const financialAnalysis: AnalysisResponse = {
  ...baseAnalysis,
  analysis_type: 'FINANCIAL_FOCUSED',
  analysis_id: 'analysis-456',
  sections_analyzed: 3,
  key_insights: ['Profit margins improved', 'Strong quarterly results'],
}

const riskAnalysis: AnalysisResponse = {
  ...baseAnalysis,
  analysis_type: 'RISK_FOCUSED',
  analysis_id: 'analysis-789',
  confidence_score: 0.92,
  sections_analyzed: 2,
  key_insights: ['Supply chain vulnerabilities identified'],
}

const businessAnalysis: AnalysisResponse = {
  ...baseAnalysis,
  analysis_type: 'BUSINESS_FOCUSED',
  analysis_id: 'analysis-012',
  confidence_score: 0.76,
  sections_analyzed: 4,
  key_insights: ['Strategic partnerships expanding', 'New product launches'],
}

// Analysis with minimal data
const minimalAnalysis: AnalysisResponse = {
  ...baseAnalysis,
  analysis_type: 'COMPREHENSIVE',
  analysis_id: 'minimal-123',
  executive_summary: undefined,
  key_insights: undefined,
  sections_analyzed: undefined,
  processing_time_seconds: undefined,
  llm_model: undefined,
}

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('AnalysisCard Component', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(
          <TestWrapper>
            <AnalysisCard analysis={comprehensiveAnalysis} />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('renders as a clickable link', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')
      expect(cardLink).toHaveAttribute('href', '/analyses/analysis-123')
    })

    it('applies correct CSS classes for hover effects', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')
      expect(cardLink).toHaveClass('hover:shadow-md', 'hover:border-primary/30')
    })

    it('applies correct layout classes', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')
      expect(cardLink).toHaveClass(
        'block',
        'bg-card',
        'rounded-lg',
        'border',
        'border-border',
        'shadow-sm'
      )
    })
  })

  describe('Analysis Type Badge', () => {
    it('displays COMPREHENSIVE type with correct styling', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Comprehensive')
      expect(badge).toHaveClass('bg-primary/10', 'text-primary', 'border-primary/20')
    })

    it('displays FINANCIAL_FOCUSED type with correct styling', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={financialAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Financial')
      expect(badge).toHaveClass('bg-emerald-50', 'text-emerald-700', 'border-emerald-200')
    })

    it('displays RISK_FOCUSED type with correct styling', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={riskAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Risk')
      expect(badge).toHaveClass('bg-red-50', 'text-red-700', 'border-red-200')
    })

    it('displays BUSINESS_FOCUSED type with correct styling', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={businessAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Business')
      expect(badge).toHaveClass('bg-teal-50', 'text-teal-700', 'border-teal-200')
    })

    it('displays appropriate icon for each analysis type', () => {
      const { rerender } = render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      // Check that icon exists (SVG should be present)
      let svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()

      // Test other types
      rerender(
        <TestWrapper>
          <AnalysisCard analysis={financialAnalysis} />
        </TestWrapper>
      )
      svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })

    it('applies consistent badge styling', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Comprehensive')
      expect(badge).toHaveClass(
        'inline-flex',
        'items-center',
        'gap-1.5',
        'px-2.5',
        'py-1',
        'rounded-full',
        'text-xs',
        'font-medium',
        'border'
      )
    })
  })

  describe('Confidence Indicator', () => {
    it('renders confidence indicator with correct props', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const confidenceIndicator = screen.getByTestId('confidence-indicator')
      expect(confidenceIndicator).toHaveAttribute('data-score', '0.88')
      expect(confidenceIndicator).toHaveAttribute('data-size', 'sm')
      expect(confidenceIndicator).toHaveTextContent('Confidence: 88%')
    })

    it('handles null confidence score', () => {
      const analysisWithNullConfidence = {
        ...comprehensiveAnalysis,
        confidence_score: null,
      }

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithNullConfidence} />
        </TestWrapper>
      )

      const confidenceIndicator = screen.getByTestId('confidence-indicator')
      expect(confidenceIndicator).toHaveTextContent('Confidence: N/A')
    })
  })

  describe('Content Preview', () => {
    it('displays executive summary when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText(/comprehensive insights into the company/)).toBeInTheDocument()
    })

    it('does not display executive summary section when not available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={minimalAnalysis} />
        </TestWrapper>
      )

      // Should not have the paragraph that would contain executive summary
      expect(screen.queryByText(/comprehensive insights/)).not.toBeInTheDocument()
    })

    it('applies correct styling to executive summary', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const summaryText = screen.getByText(/comprehensive insights into the company/)
      expect(summaryText).toHaveClass(
        'text-foreground/80',
        'text-sm',
        'leading-relaxed',
        'line-clamp-3'
      )
    })
  })

  describe('Key Metrics Display', () => {
    it('displays sections analyzed count when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('5 sections')).toBeInTheDocument()
    })

    it('displays insights count when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('3 insights')).toBeInTheDocument()
    })

    it('does not display metrics when not available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={minimalAnalysis} />
        </TestWrapper>
      )

      expect(screen.queryByText(/sections/)).not.toBeInTheDocument()
      expect(screen.queryByText(/insights/)).not.toBeInTheDocument()
    })

    it('applies correct styling to metrics', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const sectionsMetric = screen.getByText('5 sections')
      expect(sectionsMetric.parentElement).toHaveClass(
        'inline-flex',
        'items-center',
        'gap-1',
        'text-xs',
        'text-muted-foreground'
      )
    })
  })

  describe('Quick Insights Preview', () => {
    it('displays first two insights when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText(/Revenue growth of 15%/)).toBeInTheDocument()
      expect(screen.getByText(/Strong cash position/)).toBeInTheDocument()
    })

    it('shows additional insights count when more than two available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('+1 more insights')).toBeInTheDocument()
    })

    it('does not show additional count when two or fewer insights', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={financialAnalysis} />
        </TestWrapper>
      )

      expect(screen.queryByText(/more insights/)).not.toBeInTheDocument()
    })

    it('applies correct styling to insights', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const insightText = screen.getByText(/Revenue growth of 15%/)
      expect(insightText).toHaveClass('line-clamp-1')
      expect(insightText.parentElement).toHaveClass(
        'flex',
        'gap-2',
        'text-xs',
        'text-muted-foreground'
      )
    })

    it('does not render insights section when no insights available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={minimalAnalysis} />
        </TestWrapper>
      )

      // No insights bullet points should be visible
      expect(screen.queryByText(/Revenue growth/)).not.toBeInTheDocument()
    })
  })

  describe('Metadata Footer', () => {
    it('displays formatted creation date', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('Jan 15, 2024')).toBeInTheDocument()
    })

    it('displays processing time when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('32s')).toBeInTheDocument()
    })

    it('does not display processing time when not available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={minimalAnalysis} />
        </TestWrapper>
      )

      expect(screen.queryByText(/\d+s$/)).not.toBeInTheDocument()
    })

    it('displays chevron icon for navigation', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const chevronIcon = screen.getByRole('link').querySelector('svg[class*="h-4 w-4"]')
      expect(chevronIcon).toBeInTheDocument()
    })

    it('applies correct styling to metadata footer', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const dateText = screen.getByText('Jan 15, 2024')
      const footerContainer = dateText.closest('.justify-between')
      expect(footerContainer).toHaveClass(
        'flex',
        'items-center',
        'justify-between',
        'text-xs',
        'text-muted-foreground',
        'pt-4',
        'border-t',
        'border-border/50'
      )
    })
  })

  describe('LLM Model Badge', () => {
    it('displays LLM model when available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('gpt-4')).toBeInTheDocument()
    })

    it('does not display LLM model when not available', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={minimalAnalysis} />
        </TestWrapper>
      )

      expect(screen.queryByText('gpt-4')).not.toBeInTheDocument()
    })

    it('applies correct styling to LLM model badge', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const modelBadge = screen.getByText('gpt-4')
      const badgeContainer = modelBadge.closest('.bg-muted')
      expect(badgeContainer).toHaveClass(
        'mt-2',
        'inline-flex',
        'items-center',
        'px-2',
        'py-1',
        'bg-muted',
        'text-muted-foreground',
        'text-xs',
        'rounded'
      )
    })
  })

  describe('User Interactions', () => {
    it('handles click navigation', async () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')
      await user.click(cardLink)

      // Navigation is handled by React Router, just check the link is clickable
      expect(cardLink).toHaveAttribute('href', '/analyses/analysis-123')
    })

    it('handles hover interactions', async () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')

      await user.hover(cardLink)

      // Hover styles should be applied via CSS classes
      expect(cardLink).toHaveClass('hover:shadow-md', 'hover:border-primary/30')
    })

    it('provides keyboard navigation support', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardLink = screen.getByRole('link')
      expect(cardLink).not.toHaveAttribute('tabindex', '-1')
    })
  })

  describe('Responsive Design', () => {
    it('applies responsive layout classes', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const cardContent = screen.getByRole('link').firstChild
      expect(cardContent).toHaveClass('p-6')
    })

    it('handles different screen sizes gracefully', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      // Text should be responsive
      const summaryText = screen.getByText(/comprehensive insights/)
      expect(summaryText).toHaveClass('line-clamp-3')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty insights array', () => {
      const analysisWithEmptyInsights = {
        ...comprehensiveAnalysis,
        key_insights: [],
      }

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithEmptyInsights} />
        </TestWrapper>
      )

      expect(screen.queryByText(/more insights/)).not.toBeInTheDocument()
    })

    it('handles very long text content', () => {
      const analysisWithLongContent = {
        ...comprehensiveAnalysis,
        executive_summary:
          'This is a very long executive summary that should be truncated appropriately when displayed in the card format to ensure good user experience and consistent layout across all cards in the grid view.',
      }

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithLongContent} />
        </TestWrapper>
      )

      const summaryText = screen.getByText(/very long executive summary/)
      expect(summaryText).toHaveClass('line-clamp-3')
    })

    it('handles zero processing time', () => {
      const analysisWithZeroTime = {
        ...comprehensiveAnalysis,
        processing_time_seconds: 0,
      }

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithZeroTime} />
        </TestWrapper>
      )

      // When processing_time_seconds is 0, it's falsy, so it won't be displayed
      expect(screen.queryByText('0s')).not.toBeInTheDocument()
    })

    it('handles undefined sections_analyzed', () => {
      const analysisWithUndefinedSections = {
        ...comprehensiveAnalysis,
        sections_analyzed: undefined,
      }

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithUndefinedSections} />
        </TestWrapper>
      )

      expect(screen.queryByText(/sections/)).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML elements', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const link = screen.getByRole('link')
      expect(link).toBeInTheDocument()
    })

    it('provides accessible link text through content', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const link = screen.getByRole('link')
      expect(link).toHaveTextContent('Comprehensive')
      expect(link).toHaveTextContent('Jan 15, 2024')
    })

    it('maintains proper color contrast', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const badge = screen.getByText('Comprehensive')
      expect(badge).toHaveClass('text-primary')

      const metadata = screen.getByText('Jan 15, 2024')
      const metadataContainer = metadata.closest('.text-muted-foreground')
      expect(metadataContainer).toBeInTheDocument()
    })

    it('supports keyboard navigation', () => {
      render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      const link = screen.getByRole('link')
      expect(link).not.toHaveAttribute('tabindex', '-1')
    })
  })

  describe('Performance', () => {
    it('renders efficiently with large datasets', () => {
      const largeInsights = Array.from({ length: 50 }, (_, i) => `Insight ${i + 1}`)
      const analysisWithLargeData = {
        ...comprehensiveAnalysis,
        key_insights: largeInsights,
      }

      const startTime = performance.now()

      render(
        <TestWrapper>
          <AnalysisCard analysis={analysisWithLargeData} />
        </TestWrapper>
      )

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(100) // Should render quickly
    })

    it('handles component updates without issues', () => {
      const { rerender } = render(
        <TestWrapper>
          <AnalysisCard analysis={comprehensiveAnalysis} />
        </TestWrapper>
      )

      // Re-render with different analysis
      rerender(
        <TestWrapper>
          <AnalysisCard analysis={financialAnalysis} />
        </TestWrapper>
      )

      expect(screen.getByText('Financial')).toBeInTheDocument()
    })
  })
})
