import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import type {
  AnalysisResponse,
  ComprehensiveAnalysisResponse,
  SectionAnalysisResponse,
  BusinessAnalysisSection,
  RiskFactorsAnalysisSection,
  MDAAnalysisSection,
  BalanceSheetAnalysisSection,
  IncomeStatementAnalysisSection,
  CashFlowAnalysisSection,
  KeyFinancialMetric,
  RiskFactor,
} from '../api/types'

// Export format types
export type ExportFormat = 'json' | 'csv' | 'pdf' | 'xlsx'

// Loading states for export operations
export interface ExportState {
  isExporting: boolean
  progress: number
  currentStep: string
  error: string | null
}

// Export configuration options
export interface ExportOptions {
  includeMetadata?: boolean
  includeFullResults?: boolean
  includeTimestamps?: boolean
  companyName?: string
  customFilename?: string
  pdfOptions?: PDFExportOptions
}

export interface PDFExportOptions {
  format?: 'a4' | 'letter'
  orientation?: 'portrait' | 'landscape'
  includeCharts?: boolean
  includeLogo?: boolean
  customHeader?: string
}

// Exportable data structure that normalizes different analysis types
export interface ExportableAnalysisData {
  // Metadata
  analysisId: string
  companyName?: string
  filingType?: string
  analysisDate: string
  confidenceLevel: string | number

  // Core Content
  executiveSummary?: string
  filingSummary?: string
  keyInsights?: string[]
  financialHighlights?: string[]
  riskFactors?: string[]
  opportunities?: string[]

  // Processing Info
  llmProvider?: string
  llmModel?: string
  processingTime?: number

  // Detailed Analysis Data
  sectionAnalyses?: SectionAnalysisResponse[]
  totalSections?: number
  totalSubSections?: number

  // Financial Metrics (flattened for CSV export)
  keyMetrics?: Array<{
    section: string
    metricName: string
    currentValue?: string
    previousValue?: string
    direction?: string
    change?: string
    significance: string
  }>

  // Risk Summary (flattened for CSV export)
  riskSummary?: Array<{
    section: string
    riskName: string
    category: string
    severity: string
    description: string
    impact: string
    mitigation?: string
  }>
}

/**
 * Type guard to check if analysis is ComprehensiveAnalysisResponse
 */
function isComprehensiveAnalysis(
  analysis: AnalysisResponse | ComprehensiveAnalysisResponse
): analysis is ComprehensiveAnalysisResponse {
  return 'analysis_timestamp' in analysis && 'section_analyses' in analysis
}

/**
 * Transform various analysis response types to exportable format
 */
export function transformToExportableData(
  analysis: AnalysisResponse | ComprehensiveAnalysisResponse,
  options: ExportOptions = {}
): ExportableAnalysisData {
  // Handle different response types safely
  const analysisId = isComprehensiveAnalysis(analysis)
    ? 'comp_analysis_' + Date.now().toString() // ComprehensiveAnalysisResponse doesn't have analysis_id
    : analysis.analysis_id

  const analysisDate = isComprehensiveAnalysis(analysis)
    ? analysis.analysis_timestamp
    : analysis.created_at

  const processingTime = isComprehensiveAnalysis(analysis)
    ? analysis.total_processing_time_ms
    : analysis.processing_time_seconds

  const baseData: ExportableAnalysisData = {
    analysisId: analysisId || 'unknown',
    analysisDate: analysisDate || new Date().toISOString(),
    confidenceLevel: analysis.confidence_score || 'N/A',
    llmProvider: isComprehensiveAnalysis(analysis) ? undefined : analysis.llm_provider || undefined,
    llmModel: isComprehensiveAnalysis(analysis) ? undefined : analysis.llm_model || undefined,
    processingTime: processingTime || undefined,
  }

  // Handle company name from options or analysis data
  if (options.companyName) {
    baseData.companyName = options.companyName
  } else if (isComprehensiveAnalysis(analysis)) {
    baseData.companyName = analysis.company_name
  }

  // Handle filing type
  if (isComprehensiveAnalysis(analysis)) {
    baseData.filingType = analysis.filing_type
  }

  // Handle different response types
  if (isComprehensiveAnalysis(analysis)) {
    // ComprehensiveAnalysisResponse properties
    baseData.filingSummary = analysis.filing_summary
    baseData.executiveSummary = analysis.executive_summary
    baseData.keyInsights = analysis.key_insights
    baseData.financialHighlights = analysis.financial_highlights
    baseData.riskFactors = analysis.risk_factors
    baseData.opportunities = analysis.opportunities
    baseData.sectionAnalyses = analysis.section_analyses
    baseData.totalSections = analysis.total_sections_analyzed
    baseData.totalSubSections = analysis.total_sub_sections_analyzed

    // Extract flattened metrics for CSV export
    baseData.keyMetrics = extractFlattenedMetrics(analysis.section_analyses)
    baseData.riskSummary = extractFlattenedRisks(analysis.section_analyses)
  } else {
    // AnalysisResponse properties
    baseData.filingSummary = analysis.filing_summary
    baseData.executiveSummary = analysis.executive_summary
    baseData.keyInsights = analysis.key_insights
    baseData.financialHighlights = analysis.financial_highlights
    baseData.riskFactors = analysis.risk_factors
    baseData.opportunities = analysis.opportunities
  }

  return baseData
}

/**
 * Extract and flatten financial metrics from section analyses
 */
function extractFlattenedMetrics(
  sections: SectionAnalysisResponse[]
): ExportableAnalysisData['keyMetrics'] {
  const metrics: NonNullable<ExportableAnalysisData['keyMetrics']> = []

  sections.forEach((section) => {
    section.sub_sections?.forEach((subSection) => {
      const analysis = subSection.analysis

      // Extract key financial metrics
      if (analysis && typeof analysis === 'object' && 'key_financial_metrics' in analysis) {
        const keyMetrics = (analysis as unknown as Record<string, unknown>).key_financial_metrics
        if (Array.isArray(keyMetrics)) {
          keyMetrics.forEach((metric: KeyFinancialMetric) => {
            metrics.push({
              section: section.section_name,
              metricName: metric.metric_name,
              currentValue: metric.current_value || undefined,
              previousValue: metric.previous_value || undefined,
              direction: metric.direction,
              change: metric.percentage_change || undefined,
              significance: metric.significance,
            })
          })
        }
      }

      // Extract ratios from various analysis types
      if (analysis && typeof analysis === 'object' && 'key_ratios' in analysis) {
        const ratios = (analysis as unknown as Record<string, unknown>).key_ratios
        if (Array.isArray(ratios)) {
          ratios.forEach((ratio: Record<string, unknown>) => {
            metrics.push({
              section: section.section_name,
              metricName: String(ratio.ratio_name || 'N/A'),
              currentValue: ratio.current_value?.toString(),
              previousValue: ratio.previous_value?.toString(),
              direction: 'N/A',
              change: 'N/A',
              significance: String(ratio.interpretation || 'N/A'),
            })
          })
        }
      }
    })
  })

  return metrics
}

/**
 * Extract and flatten risk factors from section analyses
 */
function extractFlattenedRisks(
  sections: SectionAnalysisResponse[]
): ExportableAnalysisData['riskSummary'] {
  const risks: NonNullable<ExportableAnalysisData['riskSummary']> = []

  sections.forEach((section) => {
    section.sub_sections?.forEach((subSection) => {
      const analysis = subSection.analysis

      if (analysis && typeof analysis === 'object' && 'risk_factors' in analysis) {
        const riskFactors = (analysis as unknown as Record<string, unknown>).risk_factors
        if (Array.isArray(riskFactors)) {
          riskFactors.forEach((risk: RiskFactor) => {
            risks.push({
              section: section.section_name,
              riskName: risk.risk_name,
              category: risk.category,
              severity: risk.severity,
              description: risk.description,
              impact: risk.potential_impact,
              mitigation: risk.mitigation_measures?.join('; ') || undefined,
            })
          })
        }
      }
    })
  })

  return risks
}

/**
 * Extract and format comprehensive schema data from sub-sections
 */
function extractSchemaData(sections: SectionAnalysisResponse[]): {
  businessAnalysis: Array<{ section: string; data: BusinessAnalysisSection }>
  riskAnalysis: Array<{ section: string; data: RiskFactorsAnalysisSection }>
  mdaAnalysis: Array<{ section: string; data: MDAAnalysisSection }>
  balanceSheetAnalysis: Array<{ section: string; data: BalanceSheetAnalysisSection }>
  incomeStatementAnalysis: Array<{ section: string; data: IncomeStatementAnalysisSection }>
  cashFlowAnalysis: Array<{ section: string; data: CashFlowAnalysisSection }>
} {
  const businessAnalysis: Array<{ section: string; data: BusinessAnalysisSection }> = []
  const riskAnalysis: Array<{ section: string; data: RiskFactorsAnalysisSection }> = []
  const mdaAnalysis: Array<{ section: string; data: MDAAnalysisSection }> = []
  const balanceSheetAnalysis: Array<{ section: string; data: BalanceSheetAnalysisSection }> = []
  const incomeStatementAnalysis: Array<{ section: string; data: IncomeStatementAnalysisSection }> =
    []
  const cashFlowAnalysis: Array<{ section: string; data: CashFlowAnalysisSection }> = []

  sections.forEach((section) => {
    section.sub_sections?.forEach((subSection) => {
      const analysis = subSection.analysis
      if (!analysis) return

      // Check schema type and categorize accordingly
      switch (subSection.schema_type) {
        case 'business_analysis':
          businessAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as BusinessAnalysisSection,
          })
          break
        case 'risk_factors_analysis':
          riskAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as RiskFactorsAnalysisSection,
          })
          break
        case 'mda_analysis':
          mdaAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as MDAAnalysisSection,
          })
          break
        case 'balance_sheet_analysis':
          balanceSheetAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as BalanceSheetAnalysisSection,
          })
          break
        case 'income_statement_analysis':
          incomeStatementAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as IncomeStatementAnalysisSection,
          })
          break
        case 'cash_flow_analysis':
          cashFlowAnalysis.push({
            section: `${section.section_name} - ${subSection.sub_section_name}`,
            data: analysis as CashFlowAnalysisSection,
          })
          break
      }
    })
  })

  return {
    businessAnalysis,
    riskAnalysis,
    mdaAnalysis,
    balanceSheetAnalysis,
    incomeStatementAnalysis,
    cashFlowAnalysis,
  }
}

/**
 * Format business analysis data for readable output
 */
function formatBusinessAnalysisForDisplay(
  data: BusinessAnalysisSection,
  sectionName: string
): string {
  const sections: string[] = []

  sections.push(`=== BUSINESS ANALYSIS: ${sectionName} ===`)

  // Operational Overview
  if (data.operational_overview) {
    sections.push('OPERATIONAL OVERVIEW:')
    sections.push(`Description: ${data.operational_overview.description}`)
    sections.push(`Industry: ${data.operational_overview.industry_classification}`)
    sections.push(`Primary Markets: ${data.operational_overview.primary_markets.join(', ')}`)
    if (data.operational_overview.target_customers) {
      sections.push(`Target Customers: ${data.operational_overview.target_customers}`)
    }
    if (data.operational_overview.business_model) {
      sections.push(`Business Model: ${data.operational_overview.business_model}`)
    }
    sections.push('')
  }

  // Key Products
  if (data.key_products?.length > 0) {
    sections.push('KEY PRODUCTS:')
    data.key_products.forEach((product, index) => {
      sections.push(`${index + 1}. ${product.name}`)
      sections.push(`   Description: ${product.description}`)
      if (product.significance) {
        sections.push(`   Significance: ${product.significance}`)
      }
    })
    sections.push('')
  }

  // Competitive Advantages
  if (data.competitive_advantages?.length > 0) {
    sections.push('COMPETITIVE ADVANTAGES:')
    data.competitive_advantages.forEach((advantage, index) => {
      sections.push(`${index + 1}. ${advantage.advantage}`)
      sections.push(`   Description: ${advantage.description}`)
      if (advantage.competitors?.length) {
        sections.push(`   Competitors: ${advantage.competitors.join(', ')}`)
      }
      if (advantage.sustainability) {
        sections.push(`   Sustainability: ${advantage.sustainability}`)
      }
    })
    sections.push('')
  }

  // Strategic Initiatives
  if (data.strategic_initiatives?.length > 0) {
    sections.push('STRATEGIC INITIATIVES:')
    data.strategic_initiatives.forEach((initiative, index) => {
      sections.push(`${index + 1}. ${initiative.name}`)
      sections.push(`   Description: ${initiative.description}`)
      sections.push(`   Impact: ${initiative.impact}`)
      if (initiative.timeframe) {
        sections.push(`   Timeframe: ${initiative.timeframe}`)
      }
      if (initiative.resource_allocation) {
        sections.push(`   Resource Allocation: ${initiative.resource_allocation}`)
      }
    })
    sections.push('')
  }

  return sections.join('\n')
}

/**
 * Format MDA analysis data for readable output
 */
function formatMDAAnalysisForDisplay(data: MDAAnalysisSection, sectionName: string): string {
  const sections: string[] = []

  sections.push(`=== MDA ANALYSIS: ${sectionName} ===`)

  // Executive Overview
  if (data.executive_overview) {
    sections.push('EXECUTIVE OVERVIEW:')
    sections.push(data.executive_overview)
    sections.push('')
  }

  // Key Financial Metrics
  if (data.key_financial_metrics?.length > 0) {
    sections.push('KEY FINANCIAL METRICS:')
    data.key_financial_metrics.forEach((metric) => {
      sections.push(`• ${metric.metric_name}`)
      if (metric.current_value) sections.push(`  Current: ${metric.current_value}`)
      if (metric.previous_value) sections.push(`  Previous: ${metric.previous_value}`)
      sections.push(`  Direction: ${metric.direction}`)
      if (metric.percentage_change) sections.push(`  Change: ${metric.percentage_change}`)
      sections.push(`  Explanation: ${metric.explanation}`)
      sections.push(`  Significance: ${metric.significance}`)
      sections.push('')
    })
  }

  // Revenue Analysis
  if (data.revenue_analysis) {
    sections.push('REVENUE ANALYSIS:')
    sections.push(`Performance: ${data.revenue_analysis.total_revenue_performance}`)
    if (data.revenue_analysis.revenue_drivers.length > 0) {
      sections.push('Drivers:')
      data.revenue_analysis.revenue_drivers.forEach((driver) => sections.push(`  • ${driver}`))
    }
    if (data.revenue_analysis.revenue_headwinds?.length) {
      sections.push('Headwinds:')
      data.revenue_analysis.revenue_headwinds.forEach((headwind) =>
        sections.push(`  • ${headwind}`)
      )
    }
    sections.push('')
  }

  // Profitability Analysis
  if (data.profitability_analysis) {
    sections.push('PROFITABILITY ANALYSIS:')
    if (data.profitability_analysis.gross_margin_analysis) {
      sections.push(`Gross Margin: ${data.profitability_analysis.gross_margin_analysis}`)
    }
    if (data.profitability_analysis.operating_margin_analysis) {
      sections.push(`Operating Margin: ${data.profitability_analysis.operating_margin_analysis}`)
    }
    if (data.profitability_analysis.net_margin_analysis) {
      sections.push(`Net Margin: ${data.profitability_analysis.net_margin_analysis}`)
    }
    sections.push('')
  }

  // Outlook Summary
  if (data.outlook_summary) {
    sections.push('OUTLOOK:')
    sections.push(`Summary: ${data.outlook_summary}`)
    sections.push(`Sentiment: ${data.outlook_sentiment}`)
    sections.push('')
  }

  return sections.join('\n')
}

/**
 * Format financial statement analysis for readable output
 */
function formatFinancialStatementForDisplay(
  data: BalanceSheetAnalysisSection | IncomeStatementAnalysisSection | CashFlowAnalysisSection,
  sectionName: string,
  statementType: string
): string {
  const sections: string[] = []

  sections.push(`=== ${statementType.toUpperCase()} ANALYSIS: ${sectionName} ===`)

  // Common fields
  if ('section_summary' in data && data.section_summary) {
    sections.push('SUMMARY:')
    sections.push(data.section_summary)
    sections.push('')
  }

  if ('period_covered' in data && data.period_covered) {
    sections.push(`Period Covered: ${data.period_covered}`)
    sections.push('')
  }

  if ('overall_trend' in data && data.overall_trend) {
    sections.push(`Overall Trend: ${data.overall_trend}`)
    sections.push('')
  }

  // Key Ratios
  if ('key_ratios' in data && data.key_ratios?.length > 0) {
    sections.push('KEY RATIOS:')
    data.key_ratios.forEach((ratio) => {
      sections.push(`• ${ratio.ratio_name}`)
      if (ratio.current_value !== null) sections.push(`  Current: ${ratio.current_value}`)
      if (ratio.previous_value !== null) sections.push(`  Previous: ${ratio.previous_value}`)
      if (ratio.industry_benchmark !== null)
        sections.push(`  Industry Benchmark: ${ratio.industry_benchmark}`)
      sections.push(`  Interpretation: ${ratio.interpretation}`)
      sections.push('')
    })
  }

  // Strengths
  if ('strengths' in data && data.strengths?.length > 0) {
    sections.push('STRENGTHS:')
    data.strengths.forEach((strength) => sections.push(`• ${strength}`))
    sections.push('')
  }

  // Concerns
  if ('concerns' in data && data.concerns?.length > 0) {
    sections.push('CONCERNS:')
    data.concerns.forEach((concern) => sections.push(`• ${concern}`))
    sections.push('')
  }

  // Year-over-year changes
  if ('year_over_year_changes' in data && data.year_over_year_changes?.length > 0) {
    sections.push('YEAR-OVER-YEAR CHANGES:')
    data.year_over_year_changes.forEach((change) => sections.push(`• ${change}`))
    sections.push('')
  }

  // Notable Items
  if ('notable_items' in data && data.notable_items?.length > 0) {
    sections.push('NOTABLE ITEMS:')
    data.notable_items.forEach((item) => sections.push(`• ${item}`))
    sections.push('')
  }

  // Management Commentary
  if ('management_commentary' in data && data.management_commentary) {
    sections.push('MANAGEMENT COMMENTARY:')
    sections.push(data.management_commentary)
    sections.push('')
  }

  // Balance Sheet Specific
  if ('liquidity_position' in data && data.liquidity_position) {
    sections.push(`Liquidity Position: ${data.liquidity_position}`)
  }
  if ('debt_level' in data && data.debt_level) {
    sections.push(`Debt Level: ${data.debt_level}`)
  }

  return sections.join('\n')
}

/**
 * Generate filename with timestamp and company info
 */
export function generateFilename(
  data: ExportableAnalysisData,
  format: ExportFormat,
  customFilename?: string
): string {
  if (customFilename) {
    return `${customFilename}.${format}`
  }

  const timestamp = new Date().toISOString().split('T')[0]
  const companyPart = data.companyName ? `_${data.companyName.replace(/[^a-zA-Z0-9]/g, '_')}` : ''
  const filingPart = data.filingType ? `_${data.filingType}` : ''

  return `aperilex_analysis${companyPart}${filingPart}_${timestamp}.${format}`
}

/**
 * Export analysis data as JSON
 */
export function exportAsJSON(
  data: ExportableAnalysisData,
  options: ExportOptions = {}
): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      // Fixed: Always include all available data by default
      // The includeFullResults option is now informational only
      const exportData = data

      const jsonString = JSON.stringify(exportData, null, 2)
      const blob = new Blob([jsonString], { type: 'application/json' })
      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = url
      link.download = generateFilename(data, 'json', options.customFilename)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      resolve()
    } catch (error) {
      reject(
        new Error(`JSON export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      )
    }
  })
}

/**
 * Export analysis data as CSV
 */
export function exportAsCSV(
  data: ExportableAnalysisData,
  options: ExportOptions = {}
): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const csvContent = generateCSVContent(data, options)
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = url
      link.download = generateFilename(data, 'csv', options.customFilename)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      resolve()
    } catch (error) {
      reject(
        new Error(`CSV export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      )
    }
  })
}

/**
 * Generate CSV content from analysis data
 */
function generateCSVContent(data: ExportableAnalysisData, options: ExportOptions): string {
  const sections: string[] = []

  // Metadata section
  if (options.includeMetadata !== false) {
    sections.push('=== ANALYSIS METADATA ===')
    sections.push('Field,Value')
    sections.push(`Analysis ID,${data.analysisId}`)
    sections.push(`Company,"${data.companyName || 'N/A'}"`)
    sections.push(`Filing Type,${data.filingType || 'N/A'}`)
    sections.push(`Analysis Date,${data.analysisDate}`)
    sections.push(`Confidence Level,${data.confidenceLevel}`)
    sections.push(`LLM Provider,${data.llmProvider || 'N/A'}`)
    sections.push(`LLM Model,${data.llmModel || 'N/A'}`)
    sections.push(`Processing Time,${data.processingTime || 'N/A'}`)
    sections.push('')
  }

  // Executive Summary section
  if (data.executiveSummary) {
    sections.push('=== EXECUTIVE SUMMARY ===')
    sections.push('Summary')
    sections.push(`"${data.executiveSummary.replace(/"/g, '""')}"`)
    sections.push('')
  }

  // Filing Summary section
  if (data.filingSummary) {
    sections.push('=== FILING SUMMARY ===')
    sections.push('Summary')
    sections.push(`"${data.filingSummary.replace(/"/g, '""')}"`)
    sections.push('')
  }

  // Key Insights section
  if (data.keyInsights && data.keyInsights.length > 0) {
    sections.push('=== KEY INSIGHTS ===')
    sections.push('Insight')
    data.keyInsights.forEach((insight) => {
      sections.push(`"${insight.replace(/"/g, '""')}"`)
    })
    sections.push('')
  }

  // Financial Highlights section
  if (data.financialHighlights && data.financialHighlights.length > 0) {
    sections.push('=== FINANCIAL HIGHLIGHTS ===')
    sections.push('Highlight')
    data.financialHighlights.forEach((highlight) => {
      sections.push(`"${highlight.replace(/"/g, '""')}"`)
    })
    sections.push('')
  }

  // Risk Factors section
  if (data.riskFactors && data.riskFactors.length > 0) {
    sections.push('=== RISK FACTORS ===')
    sections.push('Risk Factor')
    data.riskFactors.forEach((risk) => {
      sections.push(`"${risk.replace(/"/g, '""')}"`)
    })
    sections.push('')
  }

  // Financial Metrics section
  if (data.keyMetrics && data.keyMetrics.length > 0) {
    sections.push('=== FINANCIAL METRICS ===')
    sections.push('Section,Metric Name,Current Value,Previous Value,Direction,Change,Significance')
    data.keyMetrics.forEach((metric) => {
      sections.push(
        [
          `"${metric.section}"`,
          `"${metric.metricName}"`,
          `"${metric.currentValue || 'N/A'}"`,
          `"${metric.previousValue || 'N/A'}"`,
          `"${metric.direction || 'N/A'}"`,
          `"${metric.change || 'N/A'}"`,
          `"${metric.significance.replace(/"/g, '""')}"`,
        ].join(',')
      )
    })
    sections.push('')
  }

  // Risk Summary section
  if (data.riskSummary && data.riskSummary.length > 0) {
    sections.push('=== RISK SUMMARY ===')
    sections.push('Section,Risk Name,Category,Severity,Description,Impact,Mitigation')
    data.riskSummary.forEach((risk) => {
      sections.push(
        [
          `"${risk.section}"`,
          `"${risk.riskName}"`,
          `"${risk.category}"`,
          `"${risk.severity}"`,
          `"${risk.description.replace(/"/g, '""')}"`,
          `"${risk.impact.replace(/"/g, '""')}"`,
          `"${risk.mitigation || 'N/A'}"`,
        ].join(',')
      )
    })
    sections.push('')
  }

  // Opportunities section
  if (data.opportunities && data.opportunities.length > 0) {
    sections.push('=== OPPORTUNITIES ===')
    sections.push('Opportunity')
    data.opportunities.forEach((opportunity) => {
      sections.push(`"${opportunity.replace(/"/g, '""')}"`)
    })
    sections.push('')
  }

  // Add comprehensive schema data sections
  if (data.sectionAnalyses && data.sectionAnalyses.length > 0) {
    const schemaData = extractSchemaData(data.sectionAnalyses)

    // Business Analysis Details
    if (schemaData.businessAnalysis.length > 0) {
      sections.push('=== BUSINESS ANALYSIS DETAILS ===')
      schemaData.businessAnalysis.forEach((item) => {
        const formattedData = formatBusinessAnalysisForDisplay(item.data, item.section)
        sections.push(`"${formattedData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }

    // MDA Analysis Details
    if (schemaData.mdaAnalysis.length > 0) {
      sections.push('=== MDA ANALYSIS DETAILS ===')
      schemaData.mdaAnalysis.forEach((item) => {
        const formattedData = formatMDAAnalysisForDisplay(item.data, item.section)
        sections.push(`"${formattedData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }

    // Financial Statement Analysis Details
    if (schemaData.balanceSheetAnalysis.length > 0) {
      sections.push('=== BALANCE SHEET ANALYSIS DETAILS ===')
      schemaData.balanceSheetAnalysis.forEach((item) => {
        const formattedData = formatFinancialStatementForDisplay(
          item.data,
          item.section,
          'Balance Sheet'
        )
        sections.push(`"${formattedData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }

    if (schemaData.incomeStatementAnalysis.length > 0) {
      sections.push('=== INCOME STATEMENT ANALYSIS DETAILS ===')
      schemaData.incomeStatementAnalysis.forEach((item) => {
        const formattedData = formatFinancialStatementForDisplay(
          item.data,
          item.section,
          'Income Statement'
        )
        sections.push(`"${formattedData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }

    if (schemaData.cashFlowAnalysis.length > 0) {
      sections.push('=== CASH FLOW ANALYSIS DETAILS ===')
      schemaData.cashFlowAnalysis.forEach((item) => {
        const formattedData = formatFinancialStatementForDisplay(
          item.data,
          item.section,
          'Cash Flow'
        )
        sections.push(`"${formattedData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }

    // Comprehensive Risk Analysis Details
    if (schemaData.riskAnalysis.length > 0) {
      sections.push('=== COMPREHENSIVE RISK ANALYSIS DETAILS ===')
      schemaData.riskAnalysis.forEach((item) => {
        const riskData = item.data
        const riskSections: string[] = []

        riskSections.push(`Section: ${item.section}`)
        riskSections.push(`Executive Summary: ${riskData.executive_summary}`)
        riskSections.push('')

        if (riskData.risk_factors?.length > 0) {
          riskSections.push('DETAILED RISK FACTORS:')
          riskData.risk_factors.forEach((risk, index) => {
            riskSections.push(`${index + 1}. ${risk.risk_name} (${risk.category})`)
            riskSections.push(`   Severity: ${risk.severity}`)
            riskSections.push(`   Description: ${risk.description}`)
            riskSections.push(`   Impact: ${risk.potential_impact}`)
            if (risk.mitigation_measures?.length) {
              riskSections.push(`   Mitigation: ${risk.mitigation_measures.join('; ')}`)
            }
            if (risk.probability) riskSections.push(`   Probability: ${risk.probability}`)
            if (risk.timeline) riskSections.push(`   Timeline: ${risk.timeline}`)
            riskSections.push('')
          })
        }

        if (riskData.industry_risks) {
          riskSections.push('INDUSTRY RISKS:')
          riskSections.push(`Trends: ${riskData.industry_risks.industry_trends}`)
          if (riskData.industry_risks.competitive_pressures.length > 0) {
            riskSections.push(
              `Competitive Pressures: ${riskData.industry_risks.competitive_pressures.join('; ')}`
            )
          }
          riskSections.push('')
        }

        if (riskData.overall_risk_assessment) {
          riskSections.push(`Overall Assessment: ${riskData.overall_risk_assessment}`)
        }

        const formattedRiskData = riskSections.join('\n')
        sections.push(`"${formattedRiskData.replace(/"/g, '""')}"`)
        sections.push('')
      })
    }
  }

  return sections.join('\n')
}

/**
 * Export analysis data as Excel file
 * TEMPORARILY DISABLED due to high-severity security vulnerability in xlsx library
 */
export function exportAsXLSX(
  _data: ExportableAnalysisData,
  _options: ExportOptions = {}
): Promise<void> {
  return new Promise((_resolve, reject) => {
    reject(
      new Error(
        'Excel export is temporarily disabled due to a security vulnerability in the xlsx library. Please use CSV, JSON, or PDF export instead.'
      )
    )
  })
}

/**
 * Export analysis data as PDF
 */
export async function exportAsPDF(
  data: ExportableAnalysisData,
  elementId?: string,
  options: ExportOptions = {}
): Promise<void> {
  try {
    const pdfOptions = options.pdfOptions || {}
    const format = pdfOptions.format || 'a4'
    const orientation = pdfOptions.orientation || 'portrait'

    const pdf = new jsPDF({
      orientation,
      unit: 'mm',
      format: format === 'a4' ? 'a4' : 'letter',
    })

    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 20
    const contentWidth = pageWidth - margin * 2
    let currentY = margin

    // Helper function to add text with word wrapping
    const addText = (text: string, fontSize = 12, isBold = false) => {
      pdf.setFontSize(fontSize)
      pdf.setFont('helvetica', isBold ? 'bold' : 'normal')

      const textLines = pdf.splitTextToSize(text, contentWidth)
      if (currentY + textLines.length * fontSize * 0.35 > pageHeight - margin) {
        pdf.addPage()
        currentY = margin
      }

      pdf.text(textLines, margin, currentY)
      currentY += textLines.length * fontSize * 0.35 + 5
    }

    // Helper function to add a section header
    const addSectionHeader = (title: string) => {
      currentY += 5
      addText(title, 14, true)
      currentY += 5
    }

    // Helper function to add a table
    const addTable = (headers: string[], rows: string[][]) => {
      if (rows.length === 0) return

      // Calculate column widths
      const colWidth = contentWidth / headers.length
      const rowHeight = 8

      // Check if table fits on current page
      const tableHeight = (rows.length + 1) * rowHeight
      if (currentY + tableHeight > pageHeight - margin) {
        pdf.addPage()
        currentY = margin
      }

      // Add headers
      pdf.setFontSize(10)
      pdf.setFont('helvetica', 'bold')
      headers.forEach((header, index) => {
        const x = margin + index * colWidth
        const text = pdf.splitTextToSize(header, colWidth - 2)
        pdf.text(text, x + 1, currentY + 5)
      })
      currentY += rowHeight

      // Add rows
      pdf.setFont('helvetica', 'normal')
      rows.forEach((row) => {
        // Check if we need a new page for this row
        if (currentY + rowHeight > pageHeight - margin) {
          pdf.addPage()
          currentY = margin
        }

        row.forEach((cell, index) => {
          const x = margin + index * colWidth
          const text = pdf.splitTextToSize(String(cell), colWidth - 2)
          pdf.text(text, x + 1, currentY + 5)
        })
        currentY += rowHeight
      })

      currentY += 10
    }

    // Add header
    if (pdfOptions.customHeader) {
      addText(pdfOptions.customHeader, 16, true)
    } else {
      addText('Aperilex Financial Analysis Report', 18, true)
    }

    addText(`Generated on ${new Date().toLocaleDateString()}`, 10)
    currentY += 10

    // Add metadata
    if (options.includeMetadata !== false) {
      addSectionHeader('Analysis Information')
      addText(`Company: ${data.companyName || 'N/A'}`)
      addText(`Filing Type: ${data.filingType || 'N/A'}`)
      addText(`Analysis Date: ${new Date(data.analysisDate).toLocaleDateString()}`)
      addText(`Confidence Level: ${data.confidenceLevel}`)
      if (data.llmProvider) addText(`LLM Provider: ${data.llmProvider}`)
      if (data.llmModel) addText(`LLM Model: ${data.llmModel}`)
      if (data.processingTime) addText(`Processing Time: ${data.processingTime}ms`)
      currentY += 10
    }

    // Add executive summary
    if (data.executiveSummary) {
      addSectionHeader('Executive Summary')
      addText(data.executiveSummary)
    }

    // Add filing summary
    if (data.filingSummary) {
      addSectionHeader('Filing Summary')
      addText(data.filingSummary)
    }

    // Add key insights
    if (data.keyInsights && data.keyInsights.length > 0) {
      addSectionHeader('Key Insights')
      data.keyInsights.forEach((insight, index) => {
        addText(`${index + 1}. ${insight}`)
      })
    }

    // Add financial highlights
    if (data.financialHighlights && data.financialHighlights.length > 0) {
      addSectionHeader('Financial Highlights')
      data.financialHighlights.forEach((highlight, index) => {
        addText(`${index + 1}. ${highlight}`)
      })
    }

    // Add risk factors
    if (data.riskFactors && data.riskFactors.length > 0) {
      addSectionHeader('Risk Factors')
      data.riskFactors.forEach((risk, index) => {
        addText(`${index + 1}. ${risk}`)
      })
    }

    // Add opportunities
    if (data.opportunities && data.opportunities.length > 0) {
      addSectionHeader('Opportunities')
      data.opportunities.forEach((opportunity, index) => {
        addText(`${index + 1}. ${opportunity}`)
      })
    }

    // Add financial metrics table
    if (data.keyMetrics && data.keyMetrics.length > 0) {
      addSectionHeader('Financial Metrics')
      const headers = [
        'Section',
        'Metric',
        'Current',
        'Previous',
        'Direction',
        'Change',
        'Significance',
      ]
      const rows = data.keyMetrics.map((metric) => [
        metric.section,
        metric.metricName,
        metric.currentValue || 'N/A',
        metric.previousValue || 'N/A',
        metric.direction || 'N/A',
        metric.change || 'N/A',
        metric.significance.length > 30
          ? metric.significance.substring(0, 30) + '...'
          : metric.significance,
      ])
      addTable(headers, rows)
    }

    // Add risk summary table
    if (data.riskSummary && data.riskSummary.length > 0) {
      addSectionHeader('Risk Summary')
      const headers = ['Section', 'Risk', 'Category', 'Severity', 'Description', 'Impact']
      const rows = data.riskSummary.map((risk) => [
        risk.section,
        risk.riskName,
        risk.category,
        risk.severity,
        risk.description.length > 40 ? risk.description.substring(0, 40) + '...' : risk.description,
        risk.impact.length > 40 ? risk.impact.substring(0, 40) + '...' : risk.impact,
      ])
      addTable(headers, rows)
    }

    // Add detailed section analyses
    if (data.sectionAnalyses && data.sectionAnalyses.length > 0) {
      addSectionHeader('Detailed Section Analyses')

      data.sectionAnalyses.forEach((section, sectionIndex) => {
        if (currentY > pageHeight - 50) {
          pdf.addPage()
          currentY = margin
        }

        addText(`Section ${sectionIndex + 1}: ${section.section_name}`, 12, true)

        if (section.section_summary) {
          addText(`Summary: ${section.section_summary}`)
        }

        if (section.consolidated_insights && section.consolidated_insights.length > 0) {
          addText('Key Insights:', 11, true)
          section.consolidated_insights.forEach((insight) => {
            addText(`  • ${insight}`)
          })
        }

        if (section.overall_sentiment !== undefined) {
          addText(`Sentiment Score: ${section.overall_sentiment}`)
        }

        if (section.critical_findings && section.critical_findings.length > 0) {
          addText('Critical Findings:', 11, true)
          section.critical_findings.forEach((finding) => {
            addText(`  • ${finding}`)
          })
        }

        if (section.sub_sections && section.sub_sections.length > 0) {
          addText(`Sub-sections analyzed: ${section.sub_sections.length}`)
        }

        currentY += 10
      })

      // Add comprehensive schema data analysis
      const schemaData = extractSchemaData(data.sectionAnalyses)

      // Business Analysis Details
      if (schemaData.businessAnalysis.length > 0) {
        addSectionHeader('Comprehensive Business Analysis')
        schemaData.businessAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const formattedData = formatBusinessAnalysisForDisplay(item.data, item.section)
          addText(formattedData, 10)
          currentY += 10
        })
      }

      // MDA Analysis Details
      if (schemaData.mdaAnalysis.length > 0) {
        addSectionHeader('Management Discussion & Analysis Details')
        schemaData.mdaAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const formattedData = formatMDAAnalysisForDisplay(item.data, item.section)
          addText(formattedData, 10)
          currentY += 10
        })
      }

      // Financial Statement Analysis Details
      if (schemaData.balanceSheetAnalysis.length > 0) {
        addSectionHeader('Balance Sheet Analysis Details')
        schemaData.balanceSheetAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const formattedData = formatFinancialStatementForDisplay(
            item.data,
            item.section,
            'Balance Sheet'
          )
          addText(formattedData, 10)
          currentY += 10
        })
      }

      if (schemaData.incomeStatementAnalysis.length > 0) {
        addSectionHeader('Income Statement Analysis Details')
        schemaData.incomeStatementAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const formattedData = formatFinancialStatementForDisplay(
            item.data,
            item.section,
            'Income Statement'
          )
          addText(formattedData, 10)
          currentY += 10
        })
      }

      if (schemaData.cashFlowAnalysis.length > 0) {
        addSectionHeader('Cash Flow Analysis Details')
        schemaData.cashFlowAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const formattedData = formatFinancialStatementForDisplay(
            item.data,
            item.section,
            'Cash Flow'
          )
          addText(formattedData, 10)
          currentY += 10
        })
      }

      // Comprehensive Risk Analysis Details
      if (schemaData.riskAnalysis.length > 0) {
        addSectionHeader('Comprehensive Risk Analysis Details')
        schemaData.riskAnalysis.forEach((item) => {
          if (currentY > pageHeight - 50) {
            pdf.addPage()
            currentY = margin
          }

          const riskData = item.data

          addText(`Section: ${item.section}`, 11, true)
          addText(`Executive Summary: ${riskData.executive_summary}`)

          if (riskData.risk_factors?.length > 0) {
            addText('Detailed Risk Factors:', 11, true)
            riskData.risk_factors.forEach((risk, index) => {
              addText(`${index + 1}. ${risk.risk_name} (${risk.category})`, 10, true)
              addText(`   Severity: ${risk.severity}`)
              addText(`   Description: ${risk.description}`)
              addText(`   Impact: ${risk.potential_impact}`)
              if (risk.mitigation_measures?.length) {
                addText(`   Mitigation: ${risk.mitigation_measures.join('; ')}`)
              }
              if (risk.probability) addText(`   Probability: ${risk.probability}`)
              if (risk.timeline) addText(`   Timeline: ${risk.timeline}`)
              currentY += 5
            })
          }

          if (riskData.industry_risks) {
            addText('Industry Risks:', 11, true)
            addText(`Trends: ${riskData.industry_risks.industry_trends}`)
            if (riskData.industry_risks.competitive_pressures.length > 0) {
              addText(
                `Competitive Pressures: ${riskData.industry_risks.competitive_pressures.join('; ')}`
              )
            }
          }

          if (riskData.overall_risk_assessment) {
            addText('Overall Risk Assessment:', 11, true)
            addText(riskData.overall_risk_assessment)
          }

          currentY += 10
        })
      }
    }

    // If elementId is provided, try to capture HTML content
    if (elementId) {
      const element = document.getElementById(elementId)
      if (element) {
        try {
          const canvas = await html2canvas(element, {
            scale: 2,
            useCORS: true,
            allowTaint: true,
          })

          const imgData = canvas.toDataURL('image/png')
          const imgWidth = contentWidth
          const imgHeight = (canvas.height * imgWidth) / canvas.width

          // Add new page if needed
          if (currentY + imgHeight > pageHeight - margin) {
            pdf.addPage()
            currentY = margin
          }

          pdf.addImage(imgData, 'PNG', margin, currentY, imgWidth, imgHeight)
        } catch (canvasError) {
          console.warn('Could not capture HTML content:', canvasError)
        }
      }
    }

    // Save the PDF
    pdf.save(generateFilename(data, 'pdf', options.customFilename))
  } catch (error) {
    throw new Error(
      `PDF export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

/**
 * Main export function that handles all formats
 */
export async function exportAnalysis(
  analysis: AnalysisResponse | ComprehensiveAnalysisResponse,
  format: ExportFormat,
  options: ExportOptions = {},
  elementId?: string
): Promise<void> {
  const data = transformToExportableData(analysis, options)

  switch (format) {
    case 'json':
      return exportAsJSON(data, options)
    case 'csv':
      return exportAsCSV(data, options)
    case 'xlsx':
      return exportAsXLSX(data, options)
    case 'pdf':
      return exportAsPDF(data, elementId, options)
    default:
      throw new Error(`Unsupported export format: ${format}`)
  }
}

/**
 * Utility function to check if export is supported in current browser
 */
export function isExportSupported(format: ExportFormat): boolean {
  switch (format) {
    case 'json':
    case 'csv':
      return true
    case 'xlsx':
      return false // Temporarily disabled due to security vulnerability
    case 'pdf':
      return typeof window !== 'undefined' && 'HTMLCanvasElement' in window
    default:
      return false
  }
}

/**
 * Get export format display information
 */
export function getFormatInfo(format: ExportFormat) {
  switch (format) {
    case 'json':
      return {
        name: 'JSON',
        description: 'Complete analysis data in JSON format',
        icon: 'FileText',
        fileSize: 'Small-Medium',
      }
    case 'csv':
      return {
        name: 'CSV',
        description: 'Key insights and metrics in spreadsheet format',
        icon: 'Table',
        fileSize: 'Small',
      }
    case 'xlsx':
      return {
        name: 'Excel (Disabled)',
        description: 'Temporarily disabled due to security vulnerability',
        icon: 'FileSpreadsheet',
        fileSize: 'N/A',
      }
    case 'pdf':
      return {
        name: 'PDF',
        description: 'Professional report with visual formatting',
        icon: 'FileType',
        fileSize: 'Large',
      }
    default:
      return {
        name: 'Unknown',
        description: 'Unknown format',
        icon: 'File',
        fileSize: 'Unknown',
      }
  }
}
