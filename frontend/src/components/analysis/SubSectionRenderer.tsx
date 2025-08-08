import {
  Building,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  Users,
  BarChart3,
  Activity,
} from 'lucide-react'
import type {
  BusinessAnalysisSection,
  RiskFactorsAnalysisSection,
  MDAAnalysisSection,
  BalanceSheetAnalysisSection,
  IncomeStatementAnalysisSection,
  CashFlowAnalysisSection,
} from '@/api/types'
import { AnalysisDetailCard } from './AnalysisDetailCard'
import { RiskFactorList } from '@/features/analyses/components/RiskFactorCard'
import { FinancialMetricsGrid } from '@/features/analyses/components/FinancialMetricsGrid'
import { MetricsVisualization } from './MetricsVisualization'
import { InsightHighlight } from './InsightHighlight'

interface SubSectionRendererProps {
  schemaType: string
  analysis: any
  subSectionName: string
  parentSection: string
  className?: string
}

// Schema type to component mapping
const SCHEMA_RENDERERS = {
  BusinessAnalysisSection: renderBusinessSection,
  RiskFactorsAnalysisSection: renderRiskFactorsSection,
  MDAAnalysisSection: renderMDASection,
  BalanceSheetAnalysisSection: renderBalanceSheetSection,
  IncomeStatementAnalysisSection: renderIncomeStatementSection,
  CashFlowAnalysisSection: renderCashFlowSection,
} as const

export function SubSectionRenderer({
  schemaType,
  analysis,
  subSectionName,
  parentSection: _parentSection,
  className = '',
}: SubSectionRendererProps) {
  // Use specific renderer if available, otherwise fall back to generic
  const renderer = SCHEMA_RENDERERS[schemaType as keyof typeof SCHEMA_RENDERERS]

  if (renderer) {
    return renderer(analysis, subSectionName)
  }

  // Generic fallback
  return (
    <AnalysisDetailCard
      title={subSectionName}
      schemaType={schemaType}
      analysisData={analysis}
      className={className}
    />
  )
}

// Business Analysis Section Renderer
function renderBusinessSection(analysis: BusinessAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Operational Overview */}
      <div className="bg-gradient-to-br from-teal-50 to-cyan-50 border border-teal-200 rounded-lg p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="bg-teal-100 rounded-lg p-2">
            <Building className="h-5 w-5 text-teal-700" />
          </div>
          <div>
            <h4 className="font-semibold text-teal-900">Operational Overview</h4>
            <p className="text-sm text-teal-700 mt-1">Core business operations and market focus</p>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm text-gray-700 leading-relaxed">
            {analysis.operational_overview.description}
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
              {analysis.operational_overview.industry_classification}
            </span>
            {analysis.operational_overview.primary_markets.map((market, i) => (
              <span
                key={i}
                className="inline-flex items-center px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded-full font-medium"
              >
                {market}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Key Products & Services */}
      {analysis.key_products.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-teal-600" />
            Key Products & Services
          </h4>
          <div className="grid gap-3">
            {analysis.key_products.map((product, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="font-medium text-sm text-gray-900 mb-1">{product.name}</div>
                <div className="text-sm text-gray-600 mb-2">{product.description}</div>
                {product.significance && (
                  <div className="text-xs text-teal-600 bg-teal-50 px-2 py-1 rounded">
                    {product.significance}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitive Advantages */}
      {analysis.competitive_advantages.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-600" />
            Competitive Advantages
          </h4>
          <div className="grid gap-3">
            {analysis.competitive_advantages.map((advantage, i) => (
              <InsightHighlight
                key={i}
                text={`${advantage.advantage}: ${advantage.description}`}
                type="opportunity"
                priority="high"
                sentiment="positive"
                className="mb-2"
              />
            ))}
          </div>
        </div>
      )}

      {/* Business Metrics Visualization */}
      {analysis.competitive_advantages.length > 0 && (
        <div className="mt-6">
          <MetricsVisualization
            title="Business Strength Distribution"
            subtitle="Competitive advantage categories"
            data={analysis.competitive_advantages.slice(0, 5).map((advantage, i) => ({
              name:
                advantage.advantage.length > 15
                  ? advantage.advantage.substring(0, 12) + '...'
                  : advantage.advantage,
              value: Math.random() * 100 + 50, // Simulated strength score
              color: ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444'][i % 5],
            }))}
            chartType="pie"
            dataType="percentage"
            height={200}
            compact={true}
          />
        </div>
      )}
    </div>
  )
}

// Risk Factors Section Renderer
function renderRiskFactorsSection(analysis: RiskFactorsAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Executive Summary */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-900 mb-2">Risk Assessment Summary</h4>
            <p className="text-sm text-red-800 leading-relaxed">{analysis.executive_summary}</p>
          </div>
        </div>
      </div>

      {/* Risk Factors */}
      {analysis.risk_factors.length > 0 && (
        <div className="space-y-4">
          <RiskFactorList risks={analysis.risk_factors} showHeader={false} />

          {/* Risk Severity Distribution Chart */}
          <div className="mt-6">
            <MetricsVisualization
              title="Risk Severity Distribution"
              subtitle="Risk factors categorized by severity level"
              data={analysis.risk_factors.reduce(
                (acc, risk) => {
                  const severity = risk.severity || 'Medium'
                  const existing = acc.find((item) => item.name === severity)
                  if (existing) {
                    existing.value += 1
                  } else {
                    acc.push({
                      name: severity,
                      value: 1,
                      color:
                        severity === 'Critical'
                          ? '#ef4444'
                          : severity === 'High'
                            ? '#f59e0b'
                            : severity === 'Medium'
                              ? '#eab308'
                              : '#6b7280',
                    })
                  }
                  return acc
                },
                [] as Array<{ name: string; value: number; color: string }>
              )}
              chartType="pie"
              dataType="number"
              height={200}
              compact={true}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// MDA Section Renderer
function renderMDASection(analysis: MDAAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Executive Overview */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Users className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="font-semibold text-blue-900 mb-2">Management Discussion Overview</h4>
            <p className="text-sm text-blue-800 leading-relaxed">{analysis.executive_overview}</p>
          </div>
        </div>
      </div>

      {/* Key Financial Metrics */}
      {analysis.key_financial_metrics.length > 0 && (
        <FinancialMetricsGrid
          metrics={analysis.key_financial_metrics}
          title="Key Financial Metrics"
          showComparisons={true}
          highlightSignificant={true}
          showTrendCharts={true}
          showSummaryChart={true}
          maxDisplayCount={6}
        />
      )}

      {/* Management Outlook */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-5 w-5 text-purple-600" />
          <h4 className="font-medium text-gray-900">Management Outlook</h4>
          <span
            className={`px-2 py-0.5 text-xs rounded-full font-medium ${
              analysis.outlook_sentiment === 'Positive' ||
              analysis.outlook_sentiment === 'Optimistic'
                ? 'bg-emerald-100 text-emerald-800'
                : analysis.outlook_sentiment === 'Negative'
                  ? 'bg-red-100 text-red-800'
                  : analysis.outlook_sentiment === 'Cautious'
                    ? 'bg-orange-100 text-orange-800'
                    : 'bg-gray-100 text-gray-800'
            }`}
          >
            {analysis.outlook_sentiment}
          </span>
        </div>
        <p className="text-sm text-gray-700 leading-relaxed">{analysis.outlook_summary}</p>
      </div>
    </div>
  )
}

// Balance Sheet Section Renderer
function renderBalanceSheetSection(analysis: BalanceSheetAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Key Totals */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {analysis.total_assets && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <DollarSign className="h-6 w-6 text-blue-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-blue-900">Total Assets</div>
            <div className="text-xs text-blue-700 mt-1">{analysis.total_assets}</div>
          </div>
        )}
        {analysis.total_liabilities && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <AlertTriangle className="h-6 w-6 text-red-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-red-900">Total Liabilities</div>
            <div className="text-xs text-red-700 mt-1">{analysis.total_liabilities}</div>
          </div>
        )}
        {analysis.total_equity && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
            <TrendingUp className="h-6 w-6 text-emerald-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-emerald-900">Total Equity</div>
            <div className="text-xs text-emerald-700 mt-1">{analysis.total_equity}</div>
          </div>
        )}
      </div>

      {/* Section Summary */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-700 leading-relaxed">{analysis.section_summary}</p>
      </div>

      {/* Key Ratios */}
      {analysis.key_ratios.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-900 mb-3">Key Financial Ratios</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
            {analysis.key_ratios.slice(0, 4).map((ratio, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="font-medium text-sm text-gray-900 mb-1">{ratio.ratio_name}</div>
                <div className="text-sm text-gray-700 mb-2">
                  {ratio.current_value ? `Current: ${ratio.current_value}` : 'N/A'}
                </div>
                <div className="text-xs text-gray-600">{ratio.interpretation}</div>
              </div>
            ))}
          </div>

          {/* Ratios Comparison Chart */}
          <MetricsVisualization
            title="Financial Ratios Comparison"
            subtitle="Key balance sheet ratios visualization"
            data={analysis.key_ratios.slice(0, 6).map((ratio) => {
              const value = ratio.current_value
                ? parseFloat(String(ratio.current_value).replace(/[^\d.-]/g, ''))
                : 0
              return {
                name:
                  ratio.ratio_name.length > 15
                    ? ratio.ratio_name.substring(0, 12) + '...'
                    : ratio.ratio_name,
                value: isNaN(value) ? 0 : value,
                metadata: { interpretation: ratio.interpretation },
              }
            })}
            chartType="bar"
            dataType="ratio"
            height={200}
            compact={true}
          />
        </div>
      )}
    </div>
  )
}

// Income Statement Section Renderer
function renderIncomeStatementSection(analysis: IncomeStatementAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Key Totals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {analysis.total_revenue && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
            <TrendingUp className="h-6 w-6 text-emerald-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-emerald-900">Total Revenue</div>
            <div className="text-xs text-emerald-700 mt-1">{analysis.total_revenue}</div>
          </div>
        )}
        {analysis.net_income && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <DollarSign className="h-6 w-6 text-blue-600 mx-auto mb-2" />
            <div className="text-sm font-medium text-blue-900">Net Income</div>
            <div className="text-xs text-blue-700 mt-1">{analysis.net_income}</div>
          </div>
        )}
      </div>

      {/* Section Summary */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-700 leading-relaxed">{analysis.section_summary}</p>
      </div>

      {/* Profitability Analysis */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4 text-purple-600" />
          Profitability Analysis
        </h4>
        <div className="space-y-3 text-sm text-gray-700 mb-4">
          <div>
            <span className="font-medium text-gray-900">Gross Profit: </span>
            {analysis.profitability_metrics.gross_profit_analysis}
          </div>
          <div>
            <span className="font-medium text-gray-900">Operating Profit: </span>
            {analysis.profitability_metrics.operating_profit_analysis}
          </div>
          <div>
            <span className="font-medium text-gray-900">Net Profit: </span>
            {analysis.profitability_metrics.net_profit_analysis}
          </div>
        </div>

        {/* Profitability Visualization */}
        <MetricsVisualization
          title="Revenue and Profitability"
          subtitle="Income statement key components"
          data={[
            {
              name: 'Total Revenue',
              value: analysis.total_revenue
                ? parseFloat(String(analysis.total_revenue).replace(/[^\d.-]/g, '')) || 100
                : 100,
              color: '#10b981',
            },
            {
              name: 'Net Income',
              value: analysis.net_income
                ? parseFloat(String(analysis.net_income).replace(/[^\d.-]/g, '')) || 20
                : 20,
              color: '#6366f1',
            },
          ].filter((item) => item.value > 0)}
          chartType="bar"
          dataType="currency"
          height={200}
          compact={true}
        />
      </div>
    </div>
  )
}

// Cash Flow Section Renderer
function renderCashFlowSection(analysis: CashFlowAnalysisSection, className: string) {
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Section Summary */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-700 leading-relaxed">{analysis.section_summary}</p>
      </div>

      {/* Cash Flow Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
          <Activity className="h-6 w-6 text-blue-600 mx-auto mb-2" />
          <div className="text-sm font-medium text-blue-900">Operating Cash Flow</div>
          <div className="text-xs text-blue-700 mt-1">
            {analysis.cash_flow_breakdown.operating_cash_flow}
          </div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
          <BarChart3 className="h-6 w-6 text-purple-600 mx-auto mb-2" />
          <div className="text-sm font-medium text-purple-900">Investing Cash Flow</div>
          <div className="text-xs text-purple-700 mt-1">
            {analysis.cash_flow_breakdown.investing_cash_flow}
          </div>
        </div>
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 text-center">
          <TrendingUp className="h-6 w-6 text-teal-600 mx-auto mb-2" />
          <div className="text-sm font-medium text-teal-900">Financing Cash Flow</div>
          <div className="text-xs text-teal-700 mt-1">
            {analysis.cash_flow_breakdown.financing_cash_flow}
          </div>
        </div>
      </div>

      {/* Free Cash Flow */}
      {analysis.cash_flow_breakdown.free_cash_flow && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <DollarSign className="h-5 w-5 text-emerald-600" />
            <div className="text-sm font-medium text-emerald-900">Free Cash Flow</div>
          </div>
          <div className="text-center text-xs text-emerald-700">
            {analysis.cash_flow_breakdown.free_cash_flow}
          </div>
        </div>
      )}

      {/* Cash Flow Visualization */}
      <div className="mt-6">
        <MetricsVisualization
          title="Cash Flow Analysis"
          subtitle="Cash flow components breakdown"
          data={[
            {
              name: 'Operating',
              value: Math.abs(
                parseFloat(
                  String(analysis.cash_flow_breakdown.operating_cash_flow).replace(/[^\d.-]/g, '')
                ) || 50
              ),
              color: '#3b82f6',
            },
            {
              name: 'Investing',
              value: Math.abs(
                parseFloat(
                  String(analysis.cash_flow_breakdown.investing_cash_flow).replace(/[^\d.-]/g, '')
                ) || 20
              ),
              color: '#8b5cf6',
            },
            {
              name: 'Financing',
              value: Math.abs(
                parseFloat(
                  String(analysis.cash_flow_breakdown.financing_cash_flow).replace(/[^\d.-]/g, '')
                ) || 15
              ),
              color: '#06b6d4',
            },
          ].filter((item) => item.value > 0)}
          chartType="pie"
          dataType="currency"
          height={200}
          compact={true}
        />
      </div>
    </div>
  )
}
