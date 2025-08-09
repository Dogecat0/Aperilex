import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  transformToExportableData,
  generateFilename,
  exportAsJSON,
  isExportSupported,
  getFormatInfo,
  exportAnalysis,
  type ExportableAnalysisData,
} from './exportUtils'
import type {
  AnalysisResponse,
  ComprehensiveAnalysisResponse,
  SectionAnalysisResponse,
  BusinessAnalysisSection,
  RiskFactorsAnalysisSection,
  MDAAnalysisSection,
} from '../api/types'

// Mock jsPDF and html2canvas
vi.mock('jspdf', () => ({
  default: vi.fn().mockImplementation(() => ({
    internal: {
      pageSize: {
        getWidth: () => 210,
        getHeight: () => 297,
      },
    },
    setFontSize: vi.fn(),
    setFont: vi.fn(),
    splitTextToSize: vi.fn((text: string) => [text]),
    text: vi.fn(),
    addPage: vi.fn(),
    addImage: vi.fn(),
    save: vi.fn(),
  })),
}))

vi.mock('html2canvas', () => ({
  default: vi.fn().mockResolvedValue({
    toDataURL: () => 'data:image/png;base64,mock',
    height: 100,
    width: 200,
  }),
}))

// Mock DOM APIs
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = vi.fn()
Object.defineProperty(global, 'Blob', {
  value: class MockBlob {
    constructor(
      public content: string[],
      public options: any
    ) {}
  },
})

// Mock document methods
const mockLink = {
  href: '',
  download: '',
  click: vi.fn(),
}
global.document.createElement = vi.fn((tag) => {
  if (tag === 'a') return mockLink
  return {}
}) as any
global.document.body.appendChild = vi.fn()
global.document.body.removeChild = vi.fn()
global.document.getElementById = vi.fn()

describe('exportUtils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Sample test data
  const mockAnalysisResponse: AnalysisResponse = {
    analysis_id: 'test-analysis-1',
    filing_id: 'filing-123',
    analysis_type: 'COMPREHENSIVE',
    created_by: 'test-user',
    created_at: '2024-01-15T10:30:00Z',
    confidence_score: 0.85,
    llm_provider: 'openai',
    llm_model: 'gpt-4',
    processing_time_seconds: 45,
    filing_summary: 'Test filing summary for analysis',
    executive_summary: 'Executive summary of the analysis',
    key_insights: ['Insight 1', 'Insight 2', 'Insight 3'],
    risk_factors: ['Risk 1', 'Risk 2'],
    opportunities: ['Opportunity 1', 'Opportunity 2'],
    financial_highlights: ['Financial highlight 1', 'Financial highlight 2'],
    sections_analyzed: 5,
  }

  const mockBusinessAnalysis: BusinessAnalysisSection = {
    operational_overview: {
      description: 'Technology company focused on AI solutions',
      industry_classification: 'Technology',
      primary_markets: ['Technology'],
      target_customers: 'Enterprise customers',
      business_model: 'SaaS subscription model',
    },
    key_products: [
      {
        name: 'AI Platform',
        description: 'Main AI-powered analytics platform',
        significance: 'Core revenue driver',
      },
    ],
    competitive_advantages: [
      {
        advantage: 'Advanced AI Technology',
        description: 'Proprietary machine learning algorithms',
        competitors: ['Competitor A', 'Competitor B'],
        sustainability: 'Strong IP portfolio',
      },
    ],
    strategic_initiatives: [
      {
        name: 'Market Expansion',
        description: 'Expanding to European markets',
        impact: 'Expected 30% revenue growth',
        timeframe: '2024-2025',
        resource_allocation: '$10M investment',
      },
    ],
    business_segments: [],
    geographic_segments: [],
    supply_chain: null,
    partnerships: null,
  }

  const mockRiskAnalysis: RiskFactorsAnalysisSection = {
    executive_summary: 'Overall risk assessment shows moderate risk profile',
    risk_factors: [
      {
        risk_name: 'Market Competition',
        category: 'Market',
        description: 'Intense competition in AI market',
        severity: 'Medium',
        probability: 'High',
        potential_impact: 'Reduced market share and pricing pressure',
        mitigation_measures: ['Product differentiation', 'Cost optimization'],
        timeline: 'Ongoing',
      },
    ],
    industry_risks: {
      industry_trends: 'Rapid technological changes',
      competitive_pressures: ['Price competition', 'Feature competition'],
      market_volatility: 'High volatility in tech sector',
      disruption_threats: ['New AI technologies'],
    },
    regulatory_risks: {
      regulatory_environment: 'Evolving AI regulations',
      compliance_requirements: ['GDPR', 'AI Ethics guidelines'],
      regulatory_changes: 'New AI governance frameworks',
      enforcement_risks: 'Potential fines for non-compliance',
    },
    financial_risks: {
      credit_risk: 'Low credit risk exposure',
      liquidity_risk: 'Adequate liquidity position',
      market_risk: 'Exposed to tech market volatility',
      interest_rate_risk: 'Minimal exposure',
      currency_risk: 'Multi-currency exposure',
    },
    operational_risks: {
      key_personnel_dependence: 'Dependent on key engineers',
      supply_chain_disruption: 'Cloud infrastructure risks',
      technology_failures: 'System downtime risks',
      quality_control: 'AI model accuracy concerns',
      capacity_constraints: 'Scaling challenges',
    },
    esg_risks: null,
    risk_management_framework: 'Comprehensive risk management system',
    overall_risk_assessment: 'Moderate risk profile with good mitigation strategies',
  }

  const mockMDAAnalysis: MDAAnalysisSection = {
    executive_overview: 'Strong financial performance with growth opportunities',
    key_financial_metrics: [
      {
        metric_name: 'Revenue',
        current_value: '$100M',
        previous_value: '$80M',
        direction: 'Increased',
        percentage_change: '25%',
        explanation: 'Strong customer demand and new product launches',
        significance: 'Key growth driver',
      },
    ],
    revenue_analysis: {
      total_revenue_performance: 'Revenue increased 25% year-over-year',
      revenue_drivers: ['New customer acquisitions', 'Product expansion'],
      revenue_headwinds: ['Economic uncertainty'],
      segment_performance: ['Enterprise segment growing 30%'],
      geographic_performance: null,
      recurring_vs_onetime: 'Majority recurring revenue',
    },
    profitability_analysis: {
      gross_margin_analysis: 'Gross margin improved to 75%',
      operating_margin_analysis: 'Operating margin stable at 20%',
      net_margin_analysis: 'Net margin increased to 15%',
      cost_structure_changes: ['Reduced infrastructure costs'],
      efficiency_improvements: ['Automation initiatives'],
    },
    liquidity_analysis: {
      cash_position: 'Strong cash position of $50M',
      cash_flow_analysis: 'Positive operating cash flow',
      working_capital: 'Working capital increased',
      debt_analysis: 'Minimal debt levels',
      credit_facilities: '$25M credit line available',
      capital_allocation: 'Focused on growth investments',
    },
    operational_highlights: [
      {
        achievement: 'Launched new AI platform',
        impact: 'Increased customer engagement 40%',
        strategic_significance: 'Market differentiator',
      },
    ],
    market_conditions: [
      {
        market_description: 'Growing demand for AI solutions',
        impact_on_business: 'Positive impact on revenue',
        competitive_dynamics: 'Increased competition',
        opportunity_threats: ['Market expansion opportunities'],
      },
    ],
    forward_looking_statements: null,
    critical_accounting_policies: null,
    outlook_summary: 'Positive outlook for continued growth',
    outlook_sentiment: 'Optimistic',
    management_priorities: ['Product development', 'Market expansion'],
  }

  const mockSectionAnalysis: SectionAnalysisResponse = {
    section_name: 'Business Overview',
    section_summary: 'Comprehensive business analysis section',
    consolidated_insights: ['Key business insight 1', 'Key business insight 2'],
    overall_sentiment: 0.75,
    critical_findings: ['Critical finding 1'],
    sub_sections: [
      {
        sub_section_name: 'Business Analysis',
        processing_time_ms: 2000,
        schema_type: 'business_analysis',
        analysis: mockBusinessAnalysis,
        parent_section: 'Business Overview',
        subsection_focus: 'Business operations and strategy',
      },
      {
        sub_section_name: 'Risk Analysis',
        processing_time_ms: 1500,
        schema_type: 'risk_factors_analysis',
        analysis: mockRiskAnalysis,
        parent_section: 'Risk Factors',
        subsection_focus: 'Risk assessment and mitigation',
      },
      {
        sub_section_name: 'MDA Analysis',
        processing_time_ms: 3000,
        schema_type: 'mda_analysis',
        analysis: mockMDAAnalysis,
        parent_section: 'Management Discussion',
        subsection_focus: 'Financial analysis and outlook',
      },
    ],
    processing_time_ms: 6500,
    sub_section_count: 3,
  }

  const mockComprehensiveAnalysis: ComprehensiveAnalysisResponse = {
    filing_summary: 'Comprehensive analysis of quarterly filing',
    executive_summary: 'Strong performance with growth potential',
    key_insights: ['Key insight 1', 'Key insight 2'],
    financial_highlights: ['Revenue growth 25%', 'Margin improvement'],
    risk_factors: ['Market competition', 'Regulatory changes'],
    opportunities: ['Market expansion', 'Product innovation'],
    confidence_score: 0.88,
    section_analyses: [mockSectionAnalysis],
    total_sections_analyzed: 1,
    total_sub_sections_analyzed: 3,
    total_processing_time_ms: 6500,
    filing_type: '10-K',
    company_name: 'Test Company Inc',
    analysis_timestamp: '2024-01-15T10:30:00Z',
  }

  describe('transformToExportableData', () => {
    it('should transform AnalysisResponse to exportable format', () => {
      const result = transformToExportableData(mockAnalysisResponse)

      expect(result.analysisId).toBe('test-analysis-1')
      expect(result.analysisDate).toBe('2024-01-15T10:30:00Z')
      expect(result.confidenceLevel).toBe(0.85)
      expect(result.llmProvider).toBe('openai')
      expect(result.llmModel).toBe('gpt-4')
      expect(result.processingTime).toBe(45)
      expect(result.executiveSummary).toBe('Executive summary of the analysis')
      expect(result.keyInsights).toEqual(['Insight 1', 'Insight 2', 'Insight 3'])
      expect(result.riskFactors).toEqual(['Risk 1', 'Risk 2'])
      expect(result.opportunities).toEqual(['Opportunity 1', 'Opportunity 2'])
      expect(result.financialHighlights).toEqual(['Financial highlight 1', 'Financial highlight 2'])
    })

    it('should transform ComprehensiveAnalysisResponse to exportable format', () => {
      const result = transformToExportableData(mockComprehensiveAnalysis)

      expect(result.analysisId).toMatch(/^comp_analysis_\d+$/)
      expect(result.analysisDate).toBe('2024-01-15T10:30:00Z')
      expect(result.confidenceLevel).toBe(0.88)
      expect(result.companyName).toBe('Test Company Inc')
      expect(result.filingType).toBe('10-K')
      expect(result.processingTime).toBe(6500)
      expect(result.sectionAnalyses).toEqual([mockSectionAnalysis])
      expect(result.totalSections).toBe(1)
      expect(result.totalSubSections).toBe(3)
    })

    it('should extract flattened metrics from comprehensive analysis', () => {
      const result = transformToExportableData(mockComprehensiveAnalysis)

      expect(result.keyMetrics).toBeDefined()
      expect(result.keyMetrics).toHaveLength(1)
      expect(result.keyMetrics![0]).toEqual({
        section: 'Business Overview',
        metricName: 'Revenue',
        currentValue: '$100M',
        previousValue: '$80M',
        direction: 'Increased',
        change: '25%',
        significance: 'Key growth driver',
      })
    })

    it('should extract flattened risks from comprehensive analysis', () => {
      const result = transformToExportableData(mockComprehensiveAnalysis)

      expect(result.riskSummary).toBeDefined()
      expect(result.riskSummary).toHaveLength(1)
      expect(result.riskSummary![0]).toEqual({
        section: 'Business Overview',
        riskName: 'Market Competition',
        category: 'Market',
        severity: 'Medium',
        description: 'Intense competition in AI market',
        impact: 'Reduced market share and pricing pressure',
        mitigation: 'Product differentiation; Cost optimization',
      })
    })
  })

  describe('generateFilename', () => {
    it('should generate filename with timestamp and company info', () => {
      const data: ExportableAnalysisData = {
        analysisId: 'test-1',
        analysisDate: '2024-01-15T10:30:00Z',
        confidenceLevel: 0.85,
        companyName: 'Test Company',
        filingType: '10-K',
      }

      const filename = generateFilename(data, 'json')

      expect(filename).toMatch(/^aperilex_analysis_Test_Company_10-K_\d{4}-\d{2}-\d{2}\.json$/)
    })

    it('should use custom filename when provided', () => {
      const data: ExportableAnalysisData = {
        analysisId: 'test-1',
        analysisDate: '2024-01-15T10:30:00Z',
        confidenceLevel: 0.85,
      }

      const filename = generateFilename(data, 'csv', 'custom_analysis_report')

      expect(filename).toBe('custom_analysis_report.csv')
    })
  })

  describe('export format support', () => {
    it('should correctly identify supported formats', () => {
      expect(isExportSupported('json')).toBe(true)
      expect(isExportSupported('csv')).toBe(true)
      expect(isExportSupported('xlsx')).toBe(false) // Temporarily disabled
      expect(isExportSupported('pdf')).toBe(true)
    })

    it('should provide correct format information', () => {
      const jsonInfo = getFormatInfo('json')
      expect(jsonInfo.name).toBe('JSON')
      expect(jsonInfo.description).toContain('Complete analysis data')

      const csvInfo = getFormatInfo('csv')
      expect(csvInfo.name).toBe('CSV')
      expect(csvInfo.description).toContain('spreadsheet format')

      const xlsxInfo = getFormatInfo('xlsx')
      expect(xlsxInfo.name).toBe('Excel (Disabled)')
      expect(xlsxInfo.description).toContain('security vulnerability')

      const pdfInfo = getFormatInfo('pdf')
      expect(pdfInfo.name).toBe('PDF')
      expect(pdfInfo.description).toContain('Professional report')
    })
  })

  describe('exportAsJSON', () => {
    it('should export analysis as JSON file', async () => {
      const data: ExportableAnalysisData = {
        analysisId: 'test-1',
        analysisDate: '2024-01-15T10:30:00Z',
        confidenceLevel: 0.85,
        executiveSummary: 'Test executive summary',
        keyInsights: ['Insight 1', 'Insight 2'],
      }

      await exportAsJSON(data)

      expect(global.URL.createObjectURL).toHaveBeenCalled()
      expect(mockLink.click).toHaveBeenCalled()
      expect(mockLink.download).toMatch(/\.json$/)
      expect(global.URL.revokeObjectURL).toHaveBeenCalled()
    })
  })

  describe('exportAnalysis main function', () => {
    it('should route to correct export function based on format', async () => {
      // Test JSON export
      await exportAnalysis(mockAnalysisResponse, 'json')
      expect(global.URL.createObjectURL).toHaveBeenCalled()

      vi.clearAllMocks()

      // Test CSV export
      await exportAnalysis(mockAnalysisResponse, 'csv')
      expect(global.URL.createObjectURL).toHaveBeenCalled()

      // Test XLSX export (should throw error)
      await expect(exportAnalysis(mockAnalysisResponse, 'xlsx')).rejects.toThrow(
        'Excel export is temporarily disabled'
      )

      // Test unsupported format
      await expect(exportAnalysis(mockAnalysisResponse, 'invalid' as any)).rejects.toThrow(
        'Unsupported export format: invalid'
      )
    })

    it('should handle comprehensive analysis export', async () => {
      await exportAnalysis(mockComprehensiveAnalysis, 'json')
      expect(global.URL.createObjectURL).toHaveBeenCalled()
    })
  })

  describe('comprehensive data extraction', () => {
    it('should correctly extract and format business analysis data', () => {
      const data = transformToExportableData(mockComprehensiveAnalysis)

      expect(data.sectionAnalyses).toBeDefined()
      expect(data.sectionAnalyses).toHaveLength(1)

      const businessSubSection = data.sectionAnalyses![0].sub_sections.find(
        (s) => s.schema_type === 'business_analysis'
      )

      expect(businessSubSection).toBeDefined()
      expect(businessSubSection!.analysis).toEqual(mockBusinessAnalysis)
    })

    it('should correctly extract and format risk analysis data', () => {
      const data = transformToExportableData(mockComprehensiveAnalysis)

      const riskSubSection = data.sectionAnalyses![0].sub_sections.find(
        (s) => s.schema_type === 'risk_factors_analysis'
      )

      expect(riskSubSection).toBeDefined()
      expect(riskSubSection!.analysis).toEqual(mockRiskAnalysis)
    })

    it('should handle missing or incomplete section data gracefully', () => {
      const incompleteAnalysis: ComprehensiveAnalysisResponse = {
        ...mockComprehensiveAnalysis,
        section_analyses: [],
      }

      const data = transformToExportableData(incompleteAnalysis)

      expect(data.keyMetrics).toEqual([])
      expect(data.riskSummary).toEqual([])
      expect(data.sectionAnalyses).toEqual([])
    })
  })
})
