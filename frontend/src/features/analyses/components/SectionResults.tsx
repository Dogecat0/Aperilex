import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Target,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Building,
  Shield,
  Users,
  Clock,
} from 'lucide-react'
import type {
  SectionAnalysisResponse,
  BusinessAnalysisSection,
  RiskFactorsAnalysisSection,
  MDAAnalysisSection,
  BalanceSheetAnalysisSection,
  IncomeStatementAnalysisSection,
  CashFlowAnalysisSection,
} from '@/api/types'
import { GenericAnalysisSection } from './GenericAnalysisSection'

interface SectionResultsProps {
  sections: SectionAnalysisResponse[]
}

export function SectionResults({ sections }: SectionResultsProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  const toggleSection = (sectionName: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionName)) {
      newExpanded.delete(sectionName)
    } else {
      newExpanded.add(sectionName)
    }
    setExpandedSections(newExpanded)
  }

  const getSectionIcon = (sectionName: string) => {
    const name = sectionName.toLowerCase()
    if (name.includes('business')) return Building
    if (name.includes('risk')) return AlertTriangle
    if (name.includes('mda') || name.includes('management')) return Users
    if (name.includes('balance')) return DollarSign
    if (name.includes('income')) return TrendingUp
    if (name.includes('cash')) return Shield
    return Target
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment >= 0.6) return 'text-success-600 bg-success-50 border-success-200'
    if (sentiment >= 0.4) return 'text-warning-600 bg-warning-50 border-warning-200'
    if (sentiment >= 0.2) return 'text-orange-600 bg-orange-50 border-orange-200'
    return 'text-error-600 bg-error-50 border-error-200'
  }

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment >= 0.8) return 'Very Positive'
    if (sentiment >= 0.6) return 'Positive'
    if (sentiment >= 0.4) return 'Neutral'
    if (sentiment >= 0.2) return 'Cautious'
    return 'Negative'
  }

  const renderSubSectionContent = (subSection: any) => {
    const { schema_type, analysis } = subSection

    switch (schema_type) {
      case 'BusinessAnalysisSection':
        return <BusinessSubSection analysis={analysis as BusinessAnalysisSection} />
      case 'RiskFactorsAnalysisSection':
        return <RiskFactorsSubSection analysis={analysis as RiskFactorsAnalysisSection} />
      case 'MDAAnalysisSection':
        return <MDASubSection analysis={analysis as MDAAnalysisSection} />
      case 'BalanceSheetAnalysisSection':
        return <BalanceSheetSubSection analysis={analysis as BalanceSheetAnalysisSection} />
      case 'IncomeStatementAnalysisSection':
        return <IncomeStatementSubSection analysis={analysis as IncomeStatementAnalysisSection} />
      case 'CashFlowAnalysisSection':
        return <CashFlowSubSection analysis={analysis as CashFlowAnalysisSection} />
      default:
        return <GenericAnalysisSection analysis={analysis} schemaType={schema_type} />
    }
  }

  if (!sections || sections.length === 0) {
    return (
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <div className="text-center py-8">
          <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Section Analysis Available</h3>
          <p className="text-gray-500">
            This analysis doesn't contain detailed section-by-section results.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Comprehensive Section Analysis
              </h2>
              <p className="text-gray-600 text-sm mt-1">
                Detailed analysis of {sections.length} filing sections with{' '}
                {sections.reduce((acc, s) => acc + s.sub_section_count, 0)} sub-sections
              </p>
            </div>
            {sections.some((s) => s.processing_time_ms) && (
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Clock className="h-4 w-4" />
                <span>
                  {Math.round(
                    sections.reduce((acc, s) => acc + (s.processing_time_ms || 0), 0) / 1000
                  )}
                  s total
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {sections.map((section, _index) => {
            const isExpanded = expandedSections.has(section.section_name)
            const SectionIcon = getSectionIcon(section.section_name)

            return (
              <div key={section.section_name} className="p-6">
                <button
                  onClick={() => toggleSection(section.section_name)}
                  className="w-full flex items-center justify-between text-left hover:bg-gray-50 -m-2 p-2 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center text-primary-700">
                      <SectionIcon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">{section.section_name}</h3>
                      <div className="flex items-center gap-3 mt-1">
                        <div
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getSentimentColor(section.overall_sentiment)}`}
                        >
                          {getSentimentLabel(section.overall_sentiment)}
                        </div>
                        {section.sub_section_count > 0 && (
                          <span className="text-xs text-gray-500">
                            {section.sub_section_count} sub-sections
                          </span>
                        )}
                        {section.processing_time_ms && (
                          <span className="text-xs text-gray-500">
                            {Math.round(section.processing_time_ms / 1000)}s
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  )}
                </button>

                {isExpanded && (
                  <div className="mt-6 ml-13 space-y-6">
                    {/* Section Summary */}
                    {section.section_summary && (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-2">Section Summary</h4>
                        <p className="text-gray-700 leading-relaxed">{section.section_summary}</p>
                      </div>
                    )}

                    {/* Consolidated Insights */}
                    {section.consolidated_insights && section.consolidated_insights.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Key Insights</h4>
                        <ul className="space-y-2">
                          {section.consolidated_insights.map((insight, insightIndex) => (
                            <li key={insightIndex} className="flex gap-2">
                              <div className="w-1.5 h-1.5 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
                              <span className="text-gray-700">{insight}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Critical Findings */}
                    {section.critical_findings && section.critical_findings.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-error-600" />
                          Critical Findings
                        </h4>
                        <ul className="space-y-2">
                          {section.critical_findings.map((finding, findingIndex) => (
                            <li key={findingIndex} className="flex gap-2">
                              <div className="w-1.5 h-1.5 bg-error-500 rounded-full mt-2 flex-shrink-0"></div>
                              <span className="text-gray-700">{finding}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Sub-Sections */}
                    {section.sub_sections && section.sub_sections.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-4">
                          Detailed Sub-Section Analysis
                        </h4>
                        <div className="space-y-4">
                          {section.sub_sections.map((subSection, subIndex) => (
                            <div key={subIndex} className="border border-gray-200 rounded-lg">
                              <div className="p-4 bg-gray-50 border-b border-gray-200">
                                <div className="flex items-center justify-between">
                                  <h5 className="font-medium text-gray-900">
                                    {subSection.sub_section_name}
                                  </h5>
                                  <div className="flex items-center gap-2 text-xs text-gray-500">
                                    <span className="capitalize">
                                      {subSection.schema_type.replace(/([A-Z])/g, ' $1').trim()}
                                    </span>
                                    {subSection.processing_time_ms && (
                                      <span>
                                        • {Math.round(subSection.processing_time_ms / 1000)}s
                                      </span>
                                    )}
                                  </div>
                                </div>
                                {subSection.subsection_focus && (
                                  <p className="text-sm text-gray-600 mt-1">
                                    {subSection.subsection_focus}
                                  </p>
                                )}
                              </div>
                              <div className="p-4">{renderSubSectionContent(subSection)}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// Sub-section component implementations
function BusinessSubSection({ analysis }: { analysis: BusinessAnalysisSection }) {
  return (
    <div className="space-y-4">
      {/* Operational Overview */}
      <div>
        <h6 className="font-medium text-gray-900 mb-2">Operational Overview</h6>
        <div className="text-sm text-gray-700 space-y-2">
          <p>{analysis.operational_overview.description}</p>
          <div className="flex flex-wrap gap-2 mt-2">
            <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
              {analysis.operational_overview.industry_classification}
            </span>
            {analysis.operational_overview.primary_markets.map((market, i) => (
              <span
                key={i}
                className="inline-flex items-center px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded"
              >
                {market}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Key Products */}
      {analysis.key_products.length > 0 && (
        <div>
          <h6 className="font-medium text-gray-900 mb-2">Key Products & Services</h6>
          <div className="space-y-2">
            {analysis.key_products.map((product, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded">
                <div className="font-medium text-sm text-gray-900">{product.name}</div>
                <div className="text-sm text-gray-600 mt-1">{product.description}</div>
                {product.significance && (
                  <div className="text-xs text-gray-500 mt-1">{product.significance}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitive Advantages */}
      {analysis.competitive_advantages.length > 0 && (
        <div>
          <h6 className="font-medium text-gray-900 mb-2">Competitive Advantages</h6>
          <div className="space-y-2">
            {analysis.competitive_advantages.map((advantage, i) => (
              <div key={i} className="p-3 bg-success-50 rounded">
                <div className="font-medium text-sm text-success-900">{advantage.advantage}</div>
                <div className="text-sm text-success-700 mt-1">{advantage.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RiskFactorsSubSection({ analysis }: { analysis: RiskFactorsAnalysisSection }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-error-50 rounded">
        <p className="text-sm text-error-800">{analysis.executive_summary}</p>
      </div>

      {analysis.risk_factors.length > 0 && (
        <div>
          <h6 className="font-medium text-gray-900 mb-2">Key Risk Factors</h6>
          <div className="space-y-2">
            {analysis.risk_factors.slice(0, 5).map((risk, i) => (
              <div key={i} className="p-3 border border-error-200 rounded">
                <div className="flex items-center gap-2 mb-1">
                  <div className="font-medium text-sm text-gray-900">{risk.risk_name}</div>
                  <span
                    className={`px-2 py-0.5 text-xs rounded ${
                      risk.severity === 'Critical'
                        ? 'bg-error-100 text-error-800'
                        : risk.severity === 'High'
                          ? 'bg-orange-100 text-orange-800'
                          : risk.severity === 'Medium'
                            ? 'bg-warning-100 text-warning-800'
                            : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {risk.severity}
                  </span>
                </div>
                <div className="text-sm text-gray-600">{risk.description}</div>
                <div className="text-sm text-gray-700 mt-1">{risk.potential_impact}</div>
              </div>
            ))}
            {analysis.risk_factors.length > 5 && (
              <div className="text-sm text-gray-500">
                +{analysis.risk_factors.length - 5} more risk factors
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function MDASubSection({ analysis }: { analysis: MDAAnalysisSection }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-blue-50 rounded">
        <p className="text-sm text-blue-800">{analysis.executive_overview}</p>
      </div>

      {/* Key Financial Metrics */}
      {analysis.key_financial_metrics.length > 0 && (
        <div>
          <h6 className="font-medium text-gray-900 mb-2">Key Financial Metrics</h6>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {analysis.key_financial_metrics.slice(0, 4).map((metric, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded">
                <div className="font-medium text-sm text-gray-900">{metric.metric_name}</div>
                <div className="flex items-center gap-2 mt-1">
                  {metric.current_value && (
                    <span className="text-sm text-gray-700">{metric.current_value}</span>
                  )}
                  {metric.direction && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        metric.direction === 'Increased'
                          ? 'bg-success-100 text-success-800'
                          : metric.direction === 'Decreased'
                            ? 'bg-error-100 text-error-800'
                            : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {metric.direction}
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-600 mt-1">{metric.explanation}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Outlook */}
      <div className="p-3 border rounded">
        <div className="flex items-center gap-2 mb-2">
          <h6 className="font-medium text-gray-900">Management Outlook</h6>
          <span
            className={`px-2 py-0.5 text-xs rounded ${
              analysis.outlook_sentiment === 'Positive' ||
              analysis.outlook_sentiment === 'Optimistic'
                ? 'bg-success-100 text-success-800'
                : analysis.outlook_sentiment === 'Negative'
                  ? 'bg-error-100 text-error-800'
                  : analysis.outlook_sentiment === 'Cautious'
                    ? 'bg-warning-100 text-warning-800'
                    : 'bg-gray-100 text-gray-800'
            }`}
          >
            {analysis.outlook_sentiment}
          </span>
        </div>
        <p className="text-sm text-gray-700">{analysis.outlook_summary}</p>
      </div>
    </div>
  )
}

function BalanceSheetSubSection({ analysis }: { analysis: BalanceSheetAnalysisSection }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4 text-center">
        {analysis.total_assets && (
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-sm font-medium text-blue-900">Total Assets</div>
            <div className="text-xs text-blue-700 mt-1">{analysis.total_assets}</div>
          </div>
        )}
        {analysis.total_liabilities && (
          <div className="p-3 bg-error-50 rounded">
            <div className="text-sm font-medium text-error-900">Total Liabilities</div>
            <div className="text-xs text-error-700 mt-1">{analysis.total_liabilities}</div>
          </div>
        )}
        {analysis.total_equity && (
          <div className="p-3 bg-success-50 rounded">
            <div className="text-sm font-medium text-success-900">Total Equity</div>
            <div className="text-xs text-success-700 mt-1">{analysis.total_equity}</div>
          </div>
        )}
      </div>

      <div className="p-3 bg-gray-50 rounded">
        <p className="text-sm text-gray-700">{analysis.section_summary}</p>
      </div>

      {/* Key Ratios */}
      {analysis.key_ratios.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {analysis.key_ratios.slice(0, 4).map((ratio, i) => (
            <div key={i} className="p-3 border rounded">
              <div className="font-medium text-sm text-gray-900">{ratio.ratio_name}</div>
              <div className="text-sm text-gray-700 mt-1">
                {ratio.current_value ? `Current: ${ratio.current_value}` : 'N/A'}
              </div>
              <div className="text-xs text-gray-600 mt-1">{ratio.interpretation}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function IncomeStatementSubSection({ analysis }: { analysis: IncomeStatementAnalysisSection }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 text-center">
        {analysis.total_revenue && (
          <div className="p-3 bg-success-50 rounded">
            <div className="text-sm font-medium text-success-900">Total Revenue</div>
            <div className="text-xs text-success-700 mt-1">{analysis.total_revenue}</div>
          </div>
        )}
        {analysis.net_income && (
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-sm font-medium text-blue-900">Net Income</div>
            <div className="text-xs text-blue-700 mt-1">{analysis.net_income}</div>
          </div>
        )}
      </div>

      <div className="p-3 bg-gray-50 rounded">
        <p className="text-sm text-gray-700">{analysis.section_summary}</p>
      </div>

      {/* Profitability Analysis */}
      <div className="space-y-2">
        <h6 className="font-medium text-gray-900">Profitability Analysis</h6>
        <div className="text-sm text-gray-700 space-y-1">
          <p>
            <strong>Gross Profit:</strong> {analysis.profitability_metrics.gross_profit_analysis}
          </p>
          <p>
            <strong>Operating Profit:</strong>{' '}
            {analysis.profitability_metrics.operating_profit_analysis}
          </p>
          <p>
            <strong>Net Profit:</strong> {analysis.profitability_metrics.net_profit_analysis}
          </p>
        </div>
      </div>
    </div>
  )
}

function CashFlowSubSection({ analysis }: { analysis: CashFlowAnalysisSection }) {
  return (
    <div className="space-y-4">
      <div className="p-3 bg-gray-50 rounded">
        <p className="text-sm text-gray-700">{analysis.section_summary}</p>
      </div>

      {/* Cash Flow Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3 bg-blue-50 rounded">
          <div className="text-sm font-medium text-blue-900">Operating Cash Flow</div>
          <div className="text-xs text-blue-700 mt-1">
            {analysis.cash_flow_breakdown.operating_cash_flow}
          </div>
        </div>
        <div className="p-3 bg-purple-50 rounded">
          <div className="text-sm font-medium text-purple-900">Investing Cash Flow</div>
          <div className="text-xs text-purple-700 mt-1">
            {analysis.cash_flow_breakdown.investing_cash_flow}
          </div>
        </div>
        <div className="p-3 bg-teal-50 rounded">
          <div className="text-sm font-medium text-teal-900">Financing Cash Flow</div>
          <div className="text-xs text-teal-700 mt-1">
            {analysis.cash_flow_breakdown.financing_cash_flow}
          </div>
        </div>
      </div>

      {/* Free Cash Flow */}
      {analysis.cash_flow_breakdown.free_cash_flow && (
        <div className="p-3 bg-success-50 rounded">
          <div className="text-sm font-medium text-success-900">Free Cash Flow</div>
          <div className="text-xs text-success-700 mt-1">
            {analysis.cash_flow_breakdown.free_cash_flow}
          </div>
        </div>
      )}
    </div>
  )
}
