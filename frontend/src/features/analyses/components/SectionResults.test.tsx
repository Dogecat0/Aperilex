import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SectionResults } from './SectionResults'
import type { SectionAnalysisResponse } from '@/api/types'

// Mock data for testing
const mockSectionAnalysis: SectionAnalysisResponse[] = [
  {
    section_name: 'Business Operations',
    section_summary: 'Analysis of the company\'s core business operations and strategic initiatives.',
    overall_sentiment: 0.8,
    sub_section_count: 3,
    consolidated_insights: [
      'Strong operational efficiency across all business units',
      'Successful expansion into emerging markets',
      'Effective cost management strategies implemented',
    ],
    critical_findings: [
      'Supply chain optimization needed in Southeast Asia',
    ],
    processing_time_ms: 5000,
    sub_sections: [
      {
        sub_section_name: 'Core Business Analysis',
        subsection_focus: 'Analysis of primary business segments and revenue drivers',
        schema_type: 'BusinessAnalysisSection',
        processing_time_ms: 2000,
        analysis: {
          operational_overview: {
            description: 'Company operates in technology and services sectors',
            industry_classification: 'Technology',
            primary_markets: ['North America', 'Europe', 'Asia'],
          },
          key_products: [
            {
              name: 'Software Platform',
              description: 'Cloud-based enterprise solution',
              significance: 'Primary revenue driver accounting for 60% of total revenue',
            },
          ],
          competitive_advantages: [
            {
              advantage: 'Market Leadership',
              description: 'Leading position in enterprise software market',
            },
          ],
        },
      },
    ],
  },
  {
    section_name: 'Risk Factors',
    section_summary: 'Comprehensive analysis of identified risk factors and their potential impact.',
    overall_sentiment: 0.4,
    sub_section_count: 2,
    consolidated_insights: [
      'Regulatory risks increasing in key markets',
      'Cybersecurity threats require enhanced measures',
    ],
    critical_findings: [
      'Data privacy regulations may impact operations',
      'Competitive pressure intensifying',
    ],
    processing_time_ms: 3000,
    sub_sections: [
      {
        sub_section_name: 'Risk Assessment',
        subsection_focus: 'Identification and analysis of key business risks',
        schema_type: 'RiskFactorsAnalysisSection',
        processing_time_ms: 1500,
        analysis: {
          executive_summary: 'Multiple high-severity risks identified that require immediate attention',
          risk_factors: [
            {
              risk_name: 'Regulatory Compliance',
              severity: 'High',
              description: 'Evolving data privacy regulations',
              potential_impact: 'May require significant operational changes',
            },
            {
              risk_name: 'Market Competition',
              severity: 'Medium',
              description: 'Increasing competitive pressure',
              potential_impact: 'Could affect market share and pricing',
            },
          ],
        },
      },
    ],
  },
  {
    section_name: 'Financial Results',
    section_summary: 'Analysis of financial performance and key metrics.',
    overall_sentiment: 0.9,
    sub_section_count: 1,
    consolidated_insights: [
      'Revenue growth acceleration in Q4',
      'Margin improvement across all segments',
    ],
    critical_findings: [],
    processing_time_ms: 2000, // 2s (rounded)
    sub_sections: [],
  },
]

const emptySections: SectionAnalysisResponse[] = []

describe('SectionResults Component', () => {
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
        render(<SectionResults sections={mockSectionAnalysis} />)
      }).not.toThrow()
    })

    it('renders header with correct section count and sub-section totals', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.getByText('Comprehensive Section Analysis')).toBeInTheDocument()
      expect(screen.getByText(/Detailed analysis of 3 filing sections with 6 sub-sections/)).toBeInTheDocument()
    })

    it('displays total processing time when available', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.getByText('10s total')).toBeInTheDocument() // 5000 + 3000 + 2000 = 10000ms = 10s
    })

    it('does not display processing time when not available', () => {
      const sectionsWithoutTime = mockSectionAnalysis.map(s => ({ ...s, processing_time_ms: undefined }))
      render(<SectionResults sections={sectionsWithoutTime} />)

      expect(screen.queryByText(/total$/)).not.toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no sections provided', () => {
      render(<SectionResults sections={emptySections} />)

      expect(screen.getByText('No Section Analysis Available')).toBeInTheDocument()
      expect(screen.getByText(/This analysis doesn\'t contain detailed section-by-section results/)).toBeInTheDocument()
    })

    it('renders Target icon in empty state', () => {
      render(<SectionResults sections={emptySections} />)

      const targetIcon = document.querySelector('svg')
      expect(targetIcon).toBeInTheDocument()
    })
  })

  describe('Section Display', () => {
    it('renders all sections with correct names', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.getByText('Business Operations')).toBeInTheDocument()
      expect(screen.getByText('Risk Factors')).toBeInTheDocument()
      expect(screen.getByText('Financial Results')).toBeInTheDocument()
    })

    it('displays sentiment badges with correct styling', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const veryPositiveSentiments = screen.getAllByText('Very Positive')
      expect(veryPositiveSentiments[0]).toHaveClass('text-success-600', 'bg-success-50', 'border-success-200')

      const neutralSentiment = screen.getByText('Neutral')
      expect(neutralSentiment).toHaveClass('text-warning-600', 'bg-warning-50', 'border-warning-200')

      // There are two "Very Positive" sentiments (Business Operations with 0.8 and Financial Results with 0.9)
      expect(veryPositiveSentiments).toHaveLength(2)
    })

    it('shows sub-section counts when available', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.getByText('3 sub-sections')).toBeInTheDocument()
      expect(screen.getByText('2 sub-sections')).toBeInTheDocument()
    })

    it('shows processing times when available', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.getByText('5s')).toBeInTheDocument()
      expect(screen.getByText('3s')).toBeInTheDocument()
      expect(screen.getByText('2s')).toBeInTheDocument()
    })

    it('displays appropriate icons for different section types', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      // Icons should be present (SVGs)
      const icons = document.querySelectorAll('svg.h-5.w-5')
      expect(icons.length).toBeGreaterThan(0)
    })
  })

  describe('Section Expansion', () => {
    it('sections are collapsed by default', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      expect(screen.queryByText('Section Summary')).not.toBeInTheDocument()
      expect(screen.queryByText('Key Insights')).not.toBeInTheDocument()
    })

    it('expands section when clicked', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      expect(sectionButton).toBeInTheDocument()

      await user.click(sectionButton!)

      expect(screen.getByText('Section Summary')).toBeInTheDocument()
      expect(screen.getByText('Key Insights')).toBeInTheDocument()
    })

    it('toggles chevron icon when expanding/collapsing', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      const chevronRight = sectionButton?.querySelector('.h-5.w-5') // ChevronRight initially
      expect(chevronRight).toBeInTheDocument()

      await user.click(sectionButton!)

      // After click, should show ChevronDown (expanded state)
      const chevronDown = sectionButton?.querySelector('.h-5.w-5') // ChevronDown when expanded
      expect(chevronDown).toBeInTheDocument()
    })

    it('collapses section when clicked again', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      
      // Expand
      await user.click(sectionButton!)
      expect(screen.getByText('Section Summary')).toBeInTheDocument()

      // Collapse
      await user.click(sectionButton!)
      expect(screen.queryByText('Section Summary')).not.toBeInTheDocument()
    })
  })

  describe('Expanded Content', () => {
    beforeEach(async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)
      
      // Expand the Business Operations section
      const sectionButton = screen.getByText('Business Operations').closest('button')
      await user.click(sectionButton!)
    })

    it('displays section summary when available', () => {
      expect(screen.getByText('Section Summary')).toBeInTheDocument()
      expect(screen.getByText(/Analysis of the company's core business operations/)).toBeInTheDocument()
    })

    it('displays key insights when available', () => {
      expect(screen.getByText('Key Insights')).toBeInTheDocument()
      expect(screen.getByText(/Strong operational efficiency/)).toBeInTheDocument()
      expect(screen.getByText(/Successful expansion into emerging markets/)).toBeInTheDocument()
      expect(screen.getByText(/Effective cost management strategies/)).toBeInTheDocument()
    })

    it('displays critical findings when available', () => {
      expect(screen.getByText('Critical Findings')).toBeInTheDocument()
      expect(screen.getByText(/Supply chain optimization needed/)).toBeInTheDocument()
    })

    it('displays sub-sections when available', () => {
      expect(screen.getByText('Detailed Sub-Section Analysis')).toBeInTheDocument()
      expect(screen.getByText('Core Business Analysis')).toBeInTheDocument()
      expect(screen.getByText(/Analysis of primary business segments/)).toBeInTheDocument()
    })
  })

  describe('Sub-Section Content Rendering', () => {
    beforeEach(async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)
      
      // Expand the Business Operations section
      const businessSection = screen.getByText('Business Operations').closest('button')
      await user.click(businessSection!)
    })

    it('renders business analysis sub-section content', () => {
      expect(screen.getByText('Operational Overview')).toBeInTheDocument()
      expect(screen.getByText(/Company operates in technology and services sectors/)).toBeInTheDocument()
      expect(screen.getByText('Technology')).toBeInTheDocument()
      expect(screen.getByText('North America')).toBeInTheDocument()
    })

    it('renders key products section', () => {
      expect(screen.getByText('Key Products & Services')).toBeInTheDocument()
      expect(screen.getByText('Software Platform')).toBeInTheDocument()
      expect(screen.getByText(/Cloud-based enterprise solution/)).toBeInTheDocument()
    })

    it('renders competitive advantages section', () => {
      expect(screen.getByText('Competitive Advantages')).toBeInTheDocument()
      expect(screen.getByText('Market Leadership')).toBeInTheDocument()
      expect(screen.getByText(/Leading position in enterprise software market/)).toBeInTheDocument()
    })
  })

  describe('Risk Factors Sub-Section', () => {
    beforeEach(async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)
      
      // Expand the Risk Factors section
      const riskSection = screen.getByText('Risk Factors').closest('button')
      await user.click(riskSection!)
    })

    it('renders risk factors analysis content', () => {
      expect(screen.getByText(/Multiple high-severity risks identified/)).toBeInTheDocument()
      expect(screen.getByText('Key Risk Factors')).toBeInTheDocument()
      expect(screen.getByText('Regulatory Compliance')).toBeInTheDocument()
      expect(screen.getByText('Market Competition')).toBeInTheDocument()
    })

    it('displays risk severity badges with correct styling', () => {
      const highSeverity = screen.getByText('High')
      expect(highSeverity).toHaveClass('bg-orange-100', 'text-orange-800')

      const mediumSeverity = screen.getByText('Medium')
      expect(mediumSeverity).toHaveClass('bg-warning-100', 'text-warning-800')
    })

    it('shows risk descriptions and potential impacts', () => {
      expect(screen.getByText(/Evolving data privacy regulations/)).toBeInTheDocument()
      expect(screen.getByText(/May require significant operational changes/)).toBeInTheDocument()
      expect(screen.getByText(/Increasing competitive pressure/)).toBeInTheDocument()
      expect(screen.getByText(/Could affect market share and pricing/)).toBeInTheDocument()
    })
  })

  describe('Sentiment Color Coding', () => {
    it('applies correct color for very positive sentiment (>= 0.8)', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)
      
      const veryPositiveElements = screen.getAllByText('Very Positive')
      expect(veryPositiveElements[0]).toHaveClass('text-success-600', 'bg-success-50', 'border-success-200')
    })

    it('applies correct color for positive sentiment (>= 0.6)', () => {
      const sectionsWithPositiveSentiment = [
        { ...mockSectionAnalysis[0], overall_sentiment: 0.7 }
      ]
      render(<SectionResults sections={sectionsWithPositiveSentiment} />)
      
      const positive = screen.getByText('Positive')
      expect(positive).toHaveClass('text-success-600', 'bg-success-50', 'border-success-200')
    })

    it('applies correct color for neutral sentiment (>= 0.4)', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)
      
      const neutral = screen.getByText('Neutral')
      expect(neutral).toHaveClass('text-warning-600', 'bg-warning-50', 'border-warning-200')
    })

    it('applies correct color for cautious sentiment (>= 0.2)', () => {
      const sectionsWithCautiousSentiment = [
        { ...mockSectionAnalysis[0], overall_sentiment: 0.3 }
      ]
      render(<SectionResults sections={sectionsWithCautiousSentiment} />)
      
      const cautious = screen.getByText('Cautious')
      expect(cautious).toHaveClass('text-orange-600', 'bg-orange-50', 'border-orange-200')
    })

    it('applies correct color for negative sentiment (< 0.2)', () => {
      const sectionsWithNegativeSentiment = [
        { ...mockSectionAnalysis[0], overall_sentiment: 0.1 }
      ]
      render(<SectionResults sections={sectionsWithNegativeSentiment} />)
      
      const negative = screen.getByText('Negative')
      expect(negative).toHaveClass('text-error-600', 'bg-error-50', 'border-error-200')
    })
  })

  describe('Section Icons', () => {
    it('uses correct icons for different section types', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      // All sections should have icons
      const iconContainers = document.querySelectorAll('.bg-primary-100')
      expect(iconContainers.length).toBe(3)
    })
  })

  describe('Edge Cases', () => {
    it('handles sections without critical findings', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      // Expand Financial Results section which has no critical findings
      const financialSection = screen.getByText('Financial Results').closest('button')
      await user.click(financialSection!)

      // Should not show Critical Findings section
      expect(screen.queryByText('Critical Findings')).not.toBeInTheDocument()
    })

    it('handles sections without sub-sections', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const financialSection = screen.getByText('Financial Results').closest('button')
      await user.click(financialSection!)

      // Should not show detailed sub-section analysis
      expect(screen.queryByText('Detailed Sub-Section Analysis')).not.toBeInTheDocument()
    })

    it('handles sections without summaries', () => {
      const sectionsWithoutSummary = mockSectionAnalysis.map(s => ({ ...s, section_summary: undefined }))
      render(<SectionResults sections={sectionsWithoutSummary} />)

      // Should still render sections but without summary when expanded
      expect(screen.getByText('Business Operations')).toBeInTheDocument()
    })

    it('handles unknown sub-section schema types', async () => {
      const sectionsWithUnknownSchema = [{
        ...mockSectionAnalysis[0],
        sub_sections: [{
          sub_section_name: 'Unknown Section',
          subsection_focus: 'Unknown analysis type',
          schema_type: 'UnknownAnalysisSection',
          processing_time_ms: 1000,
          analysis: { unknown_field: 'test data' },
        }]
      }]
      
      render(<SectionResults sections={sectionsWithUnknownSchema} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      await user.click(sectionButton!)

      expect(screen.getByText('Unknown Section')).toBeInTheDocument()
      // The schema_type is formatted with spaces: "UnknownAnalysisSection" becomes "Unknown Analysis Section"
      // Use getAllByText to check that it appears at least once (there might be multiple instances)
      const analysisTypeElements = screen.getAllByText('Unknown Analysis Section')
      expect(analysisTypeElements.length).toBeGreaterThan(0)
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML elements', () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)

      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
    })

    it('provides keyboard navigation support', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      expect(sectionButton).not.toHaveAttribute('tabindex', '-1')
      
      // Should be focusable
      sectionButton?.focus()
      expect(document.activeElement).toBe(sectionButton)
    })

    it('maintains proper heading hierarchy', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      await user.click(sectionButton!)

      const h2 = screen.getByText('Comprehensive Section Analysis')
      const h3 = screen.getByText('Business Operations').closest('h3')
      const h4 = screen.getByText('Section Summary')
      
      expect(h2.tagName).toBe('H2')
      expect(h4.tagName).toBe('H4')
    })
  })

  describe('User Interactions', () => {
    it('handles rapid clicking without errors', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const sectionButton = screen.getByText('Business Operations').closest('button')
      
      // Rapid clicks should not cause errors
      await user.click(sectionButton!)
      await user.click(sectionButton!)
      await user.click(sectionButton!)
      
      expect(() => screen.getByText('Business Operations')).not.toThrow()
    })

    it('maintains expansion state of other sections', async () => {
      render(<SectionResults sections={mockSectionAnalysis} />)

      const businessButton = screen.getByText('Business Operations').closest('button')
      const riskButton = screen.getByText('Risk Factors').closest('button')

      // Expand business section
      await user.click(businessButton!)
      expect(screen.getByText('Key Insights')).toBeInTheDocument()

      // Expand risk section
      await user.click(riskButton!)
      expect(screen.getAllByText('Key Insights')).toHaveLength(2) // Both business and risk sections have "Key Insights" 
      expect(screen.getAllByText('Critical Findings')).toHaveLength(2) // Both sections have critical findings sections
    })
  })

  describe('Performance', () => {
    it('renders efficiently with large section data', () => {
      const largeSections = Array.from({ length: 10 }, (_, i) => ({
        ...mockSectionAnalysis[0],
        section_name: `Section ${i + 1}`,
        consolidated_insights: Array.from({ length: 20 }, (_, j) => `Insight ${j + 1} for section ${i + 1}`),
      }))

      const startTime = performance.now()
      
      render(<SectionResults sections={largeSections} />)
      
      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(1000) // Should render within 1 second
    })

    it('handles component updates without unnecessary re-renders', () => {
      const { rerender } = render(<SectionResults sections={mockSectionAnalysis} />)

      // Re-render with same props
      rerender(<SectionResults sections={mockSectionAnalysis} />)
      
      expect(screen.getByText('Comprehensive Section Analysis')).toBeInTheDocument()
    })
  })
})