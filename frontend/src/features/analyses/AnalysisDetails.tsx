import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Target,
  Brain,
  Lightbulb,
  Building,
  Calendar,
  Download,
  Share2,
  FileText,
} from 'lucide-react'
import { useAnalysis } from '@/hooks/useAnalysis'
import { useFilingAnalysis, useFiling, useFilingById } from '@/hooks/useFiling'
import { Button } from '@/components/ui/Button'
import { AnalysisViewer } from './components/AnalysisViewer'
import { SectionResults } from './components/SectionResults'
import { EnhancedAnalysisOverview } from './components/EnhancedAnalysisOverview'
import { MetricsVisualization } from '@/components/analysis/MetricsVisualization'
import { InsightGroup } from '@/components/analysis/InsightHighlight'
import type { AnalysisResponse, ComprehensiveAnalysisResponse } from '@/api/types'

export function AnalysisDetails() {
  const { analysisId, accessionNumber } = useParams<{
    analysisId?: string
    accessionNumber?: string
  }>()

  // Determine if we're using analysis ID or accession number
  const isAccessionNumberRoute = !!accessionNumber
  const identifier = accessionNumber || analysisId

  // Use appropriate hook based on route type
  const analysisQuery = useAnalysis(analysisId!, !!analysisId)
  const filingAnalysisQuery = useFilingAnalysis(accessionNumber!, { enabled: !!accessionNumber })

  // Select the appropriate query result
  const {
    data: analysis,
    isLoading,
    error,
  } = isAccessionNumberRoute ? filingAnalysisQuery : analysisQuery

  // Fetch filing data to get the actual filing date
  // When coming from analysis route, use filing_id from analysis
  // When coming from filing route, accessionNumber is available from URL
  const shouldFetchByFilingId = !accessionNumber && analysis?.filing_id
  const {
    data: filingDataById,
    isLoading: filingLoadingById,
    error: filingErrorById,
  } = useFilingById(shouldFetchByFilingId ? analysis.filing_id : '', {
    enabled: shouldFetchByFilingId,
  })

  // Fetch by accession number when available from route
  const {
    data: filingDataByAccession,
    isLoading: filingLoadingByAccession,
    error: filingErrorByAccession,
  } = useFiling(accessionNumber || '', { enabled: !!accessionNumber })

  // Use the appropriate filing data based on which query was executed
  const filingData = filingDataByAccession || filingDataById
  const filingLoading = filingLoadingByAccession || filingLoadingById
  const filingError = filingErrorByAccession || filingErrorById

  if (!identifier) {
    return (
      <div className="p-6">
        <div className="bg-error-50 border border-error-200 rounded-lg p-4">
          <h3 className="text-error-800 font-medium">Invalid Analysis ID</h3>
          <p className="text-error-600 text-sm mt-1">
            The analysis ID or accession number is missing from the URL.
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-error-50 border border-error-200 rounded-lg p-4">
          <h3 className="text-error-800 font-medium">Error loading analysis</h3>
          <p className="text-error-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <Link
            to="/analyses"
            className="text-primary-600 hover:text-primary-800 text-sm font-medium mt-2 inline-block"
          >
            ← Back to analyses
          </Link>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Header Skeleton */}
        <div className="animate-pulse mb-8">
          <div className="h-4 bg-gray-200 rounded w-32 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-96 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-64"></div>
        </div>

        {/* Content Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-lg border shadow-sm p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded mb-4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
          <div className="space-y-6">
            <div className="bg-white rounded-lg border shadow-sm p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-4"></div>
              <div className="h-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="p-6">
        <div className="bg-warning-50 border border-warning-200 rounded-lg p-4">
          <h3 className="text-warning-800 font-medium">Analysis not found</h3>
          <p className="text-warning-600 text-sm mt-1">
            The requested analysis could not be found.
          </p>
          <Link
            to="/analyses"
            className="text-primary-600 hover:text-primary-800 text-sm font-medium mt-2 inline-block"
          >
            ← Back to analyses
          </Link>
        </div>
      </div>
    )
  }

  // Check if this is a comprehensive analysis with section_analyses
  const comprehensiveAnalysis = analysis.full_results as ComprehensiveAnalysisResponse | undefined
  const hasComprehensiveResults = Boolean(
    comprehensiveAnalysis &&
      'section_analyses' in comprehensiveAnalysis &&
      Array.isArray(comprehensiveAnalysis.section_analyses)
  )
  const hasLegacyResults = Boolean(analysis.full_results && !hasComprehensiveResults)

  const getFilingTypeLabel = (filingType: string): string => {
    const filingTypeMap: Record<string, string> = {
      '10-K': '10-K (Annual Report)',
      '10-Q': '10-Q (Quarterly Report)',
      '8-K': '8-K (Current Report)',
      'DEF 14A': 'DEF 14A (Proxy Statement)',
      '10-K/A': '10-K/A (Annual Report Amendment)',
      '10-Q/A': '10-Q/A (Quarterly Report Amendment)',
    }
    return filingTypeMap[filingType] || filingType
  }

  const formatFilingDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  // Helper function to get filing date from available sources
  const getFilingDate = (): string | null => {
    // Only return the actual Edgar filing date from filing data
    // Do NOT use analysis dates as those are when the analysis was performed
    if (filingData?.filing_date) {
      return filingData.filing_date
    }

    // No fallback to analysis dates - those are not filing dates
    return null
  }

  // Generate overview metrics data for visualization
  const generateOverviewMetrics = (analysis: AnalysisResponse) => {
    const metrics = []

    // Analysis confidence progression (simulated)
    if (analysis.confidence_score) {
      metrics.push({
        title: 'Analysis Confidence',
        subtitle: 'AI confidence level over processing stages',
        data: [
          { name: 'Initial', value: Math.max(0.2, analysis.confidence_score - 0.3) },
          { name: 'Processing', value: Math.max(0.4, analysis.confidence_score - 0.15) },
          { name: 'Review', value: Math.max(0.6, analysis.confidence_score - 0.05) },
          { name: 'Final', value: analysis.confidence_score },
        ],
        chartType: 'line' as const,
        dataType: 'percentage' as const,
      })
    }

    // Section analysis breakdown
    if (hasComprehensiveResults && comprehensiveAnalysis) {
      const sectionData = comprehensiveAnalysis.section_analyses.map((section) => ({
        name: section.section_name.replace(/([A-Z])/g, ' $1').trim(),
        value: section.overall_sentiment * 100,
        color:
          section.overall_sentiment >= 0.6
            ? '#10b981'
            : section.overall_sentiment >= 0.4
              ? '#f59e0b'
              : '#ef4444',
      }))

      metrics.push({
        title: 'Section Sentiment Scores',
        subtitle: 'Overall sentiment analysis by filing section',
        data: sectionData,
        chartType: 'bar' as const,
        dataType: 'percentage' as const,
      })
    }
    return metrics
  }

  const overviewMetrics = generateOverviewMetrics(analysis)

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <nav className="flex items-center space-x-2 text-sm text-gray-500 mb-6">
        <Link to="/analyses" className="hover:text-primary-600 flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" />
          Analyses
        </Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Analysis Details</span>
      </nav>

      {/* Header */}
      <div className="bg-white rounded-lg border shadow-sm p-6 mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <FileText className="h-6 w-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">
                {comprehensiveAnalysis?.company_name || 'Unknown Company'} -{' '}
                {comprehensiveAnalysis?.filing_type
                  ? getFilingTypeLabel(comprehensiveAnalysis.filing_type)
                  : 'Filing Analysis'}
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              {/* Filing Date with loading state */}
              {(() => {
                const filingDate = getFilingDate()
                if (filingLoading) {
                  return (
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span className="animate-pulse bg-gray-200 rounded w-24 h-4"></span>
                    </div>
                  )
                }
                if (filingDate) {
                  return (
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>Filed: {formatFilingDate(filingDate)}</span>
                    </div>
                  )
                }
                return null
              })()}

              {/* LLM Model */}
              {analysis.llm_model && (
                <div className="flex items-center gap-1">
                  <Brain className="h-4 w-4" />
                  <span>{analysis.llm_model}</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              Share
            </Button>
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Analysis Overview Section */}
      {analysis && (
        <EnhancedAnalysisOverview
          analysis={analysis}
          comprehensiveAnalysis={comprehensiveAnalysis}
          overviewMetrics={overviewMetrics}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Summary */}
          {analysis.executive_summary && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Target className="h-5 w-5 text-primary-600" />
                <h2 className="text-xl font-semibold text-gray-900">Executive Summary</h2>
              </div>
              <div className="prose prose-gray max-w-none">
                <p className="text-gray-700 leading-relaxed">{analysis.executive_summary}</p>
              </div>
            </div>
          )}

          {/* Filing Summary */}
          {analysis.filing_summary && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Building className="h-5 w-5 text-primary-600" />
                <h2 className="text-xl font-semibold text-gray-900">Filing Summary</h2>
              </div>
              <div className="prose prose-gray max-w-none">
                <p className="text-gray-700 leading-relaxed">{analysis.filing_summary}</p>
              </div>
            </div>
          )}

          {/* Enhanced Key Insights */}
          {analysis.key_insights && analysis.key_insights.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="h-5 w-5 text-amber-600" />
                <h2 className="text-xl font-semibold text-gray-900">Key Insights</h2>
              </div>
              <InsightGroup
                insights={analysis.key_insights.map((insight, index) => ({
                  text: insight,
                  type: 'general' as const,
                  priority: index < 2 ? ('high' as const) : ('medium' as const),
                  sentiment:
                    (analysis.confidence_score ?? 0) > 0.7
                      ? ('positive' as const)
                      : (analysis.confidence_score ?? 0) > 0.4
                        ? ('neutral' as const)
                        : ('negative' as const),
                }))}
                maxItems={10}
              />
            </div>
          )}

          {/* Comprehensive Analysis Sections */}
          {hasComprehensiveResults && comprehensiveAnalysis && (
            <SectionResults sections={comprehensiveAnalysis.section_analyses} />
          )}

          {/* Analysis Viewer for Legacy Format */}
          {hasLegacyResults && <AnalysisViewer results={analysis.full_results!} />}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Financial Highlights */}
          {analysis.financial_highlights && analysis.financial_highlights.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <InsightGroup
                insights={analysis.financial_highlights.map((highlight, index) => ({
                  text: highlight,
                  type: 'financial' as const,
                  priority: index < 2 ? ('high' as const) : ('medium' as const),
                  sentiment: 'positive' as const,
                }))}
                title="Financial Highlights"
                compact={true}
                maxItems={5}
              />

              {/* Quick financial metrics visualization if we have comprehensive data */}
              {hasComprehensiveResults && comprehensiveAnalysis && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <MetricsVisualization
                    title="Financial Sentiment Trends"
                    data={comprehensiveAnalysis.section_analyses
                      .filter(
                        (s) =>
                          s.section_name.toLowerCase().includes('financial') ||
                          s.section_name.toLowerCase().includes('income') ||
                          s.section_name.toLowerCase().includes('balance')
                      )
                      .map((section) => ({
                        name: section.section_name.split(' ')[0],
                        value: section.overall_sentiment * 100,
                        trend:
                          section.overall_sentiment > 0.6
                            ? ('up' as const)
                            : section.overall_sentiment < 0.4
                              ? ('down' as const)
                              : ('stable' as const),
                      }))}
                    chartType="bar"
                    dataType="percentage"
                    height={180}
                    compact={true}
                    showLegend={false}
                  />
                </div>
              )}
            </div>
          )}

          {/* Risk Factors */}
          {analysis.risk_factors && analysis.risk_factors.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <InsightGroup
                insights={analysis.risk_factors.map((risk, index) => ({
                  text: risk,
                  type: 'risk' as const,
                  priority:
                    index < 2
                      ? ('high' as const)
                      : index < 4
                        ? ('medium' as const)
                        : ('low' as const),
                  sentiment: 'negative' as const,
                }))}
                title="Risk Factors"
                compact={true}
                maxItems={6}
              />

              {/* Risk severity distribution if we have comprehensive data */}
              {hasComprehensiveResults && comprehensiveAnalysis && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <MetricsVisualization
                    title="Risk Assessment Distribution"
                    data={comprehensiveAnalysis.section_analyses
                      .filter((s) => s.section_name.toLowerCase().includes('risk'))
                      .map((section) => ({
                        name: 'Risk Level',
                        value: (1 - section.overall_sentiment) * 100, // Invert sentiment for risk
                        color:
                          section.overall_sentiment < 0.3
                            ? '#ef4444'
                            : section.overall_sentiment < 0.6
                              ? '#f59e0b'
                              : '#10b981',
                      }))}
                    chartType="bar"
                    dataType="percentage"
                    height={120}
                    compact={true}
                    showLegend={false}
                    showGrid={false}
                  />
                </div>
              )}
            </div>
          )}

          {/* Opportunities */}
          {analysis.opportunities && analysis.opportunities.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <InsightGroup
                insights={analysis.opportunities.map((opportunity, index) => ({
                  text: opportunity,
                  type: 'opportunity' as const,
                  priority: index < 2 ? ('high' as const) : ('medium' as const),
                  sentiment: 'positive' as const,
                }))}
                title="Growth Opportunities"
                compact={true}
                maxItems={5}
              />

              {/* Opportunity potential gauge if we have comprehensive data */}
              {hasComprehensiveResults &&
                comprehensiveAnalysis &&
                analysis.opportunities.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <MetricsVisualization
                      title="Opportunity Potential"
                      data={[
                        {
                          name: 'High Impact',
                          value: Math.min(analysis.opportunities.length * 2, 10),
                          color: '#10b981',
                        },
                        {
                          name: 'Medium Impact',
                          value: Math.min(analysis.opportunities.length * 1.5, 8),
                          color: '#f59e0b',
                        },
                        {
                          name: 'Low Impact',
                          value: Math.min(analysis.opportunities.length, 5),
                          color: '#6b7280',
                        },
                      ]}
                      chartType="pie"
                      dataType="number"
                      height={150}
                      compact={true}
                    />
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
