import { BarChart3, FileText, Activity } from 'lucide-react'
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from '@/components/ui/Card'
import { MetricsSummaryGrid } from './MetricsSummaryGrid'

import { ConfidenceIndicator } from './ConfidenceIndicator'
import { MetricsGrid } from '@/components/analysis/MetricsVisualization'
import { getAnalysisTypeColor } from '@/utils/analysisMetricsUtils'
import type { AnalysisResponse, ComprehensiveAnalysisResponse } from '@/api/types'

interface AnalysisOverviewProps {
  analysis: AnalysisResponse | ComprehensiveAnalysisResponse
  comprehensiveAnalysis?: ComprehensiveAnalysisResponse
  overviewMetrics?: any[]
  className?: string
}

export function AnalysisOverview({
  analysis,
  comprehensiveAnalysis,
  overviewMetrics,
  className = '',
}: AnalysisOverviewProps) {
  // Use comprehensiveAnalysis prop if provided, otherwise try to extract from analysis
  const comprehensiveData =
    comprehensiveAnalysis ||
    ((analysis as AnalysisResponse).full_results as ComprehensiveAnalysisResponse | undefined)

  // Check if this is a comprehensive analysis with section_analyses
  const hasComprehensiveResults = Boolean(
    comprehensiveData &&
    'section_analyses' in comprehensiveData &&
    Array.isArray(comprehensiveData.section_analyses)
  )

  const getAnalysisTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      COMPREHENSIVE: 'Comprehensive Analysis',
      FINANCIAL_FOCUSED: 'Financial Analysis',
      RISK_FOCUSED: 'Risk Analysis',
      BUSINESS_FOCUSED: 'Business Analysis',
    }
    return labels[type] || type
  }

  // Extract base analysis props for backward compatibility
  const baseAnalysis: AnalysisResponse = hasComprehensiveResults
    ? {
      analysis_id: (analysis as any).analysis_id || '',
      filing_id: (analysis as any).filing_id || '',
      analysis_type: (analysis as any).analysis_type || 'COMPREHENSIVE',
      created_by: (analysis as any).created_by || null,
      created_at: (analysis as any).created_at || new Date().toISOString(),
      confidence_score: comprehensiveData?.confidence_score || null,
      llm_provider: (analysis as any).llm_provider || null,
      llm_model: (analysis as any).llm_model || null,
      processing_time_seconds: comprehensiveData?.total_processing_time_ms
        ? Math.round(comprehensiveData.total_processing_time_ms / 1000)
        : null,
      sections_analyzed: comprehensiveData?.total_sections_analyzed || null,
      key_insights: comprehensiveData?.key_insights || [],
      risk_factors: comprehensiveData?.risk_factors || [],
      opportunities: comprehensiveData?.opportunities || [],
      financial_highlights: comprehensiveData?.financial_highlights || [],
      executive_summary: comprehensiveData?.executive_summary,
      filing_summary: comprehensiveData?.filing_summary,
      full_results: comprehensiveData,
    }
    : (analysis as AnalysisResponse)

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Analysis Metadata Header */}
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <CardTitle>Analysis Overview</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Analysis Type Badge */}
            <div className="space-y-2">
              <span className="text-sm font-medium text-foreground/80">Analysis Type</span>
              <div className="flex">
                <span
                  className={`inline-flex items-center px-3.5 py-1 rounded-full text-sm font-medium opacity-30 ${getAnalysisTypeColor(baseAnalysis.analysis_type)}`}
                >
                  {getAnalysisTypeLabel(baseAnalysis.analysis_type)}
                </span>
              </div>
            </div>

            {/* Confidence Score */}
            {baseAnalysis.confidence_score && (
              <div className="space-y-2">
                <span className="text-sm font-medium text-foreground/80">Confidence Score</span>
                <div className="flex items-center gap-2">
                  <ConfidenceIndicator score={baseAnalysis.confidence_score} showLabel />
                </div>
              </div>
            )}

            {/* LLM Provider */}
            {baseAnalysis.llm_provider && (
              <div className="space-y-2">
                <span className="text-sm font-medium text-foreground/80">LLM Provider</span>
                <div className="text-sm text-muted-foreground">{baseAnalysis.llm_provider}</div>
              </div>
            )}

            {/* LLM Model */}
            {baseAnalysis.llm_model && (
              <div className="space-y-2">
                <span className="text-sm font-medium text-foreground/80">Model</span>
                <div className="text-sm text-muted-foreground font-mono">
                  {baseAnalysis.llm_model}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics Grid */}
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <CardTitle>Key Metrics</CardTitle>
          </div>
          <CardDescription>Measurements of analysis coverage and performance</CardDescription>
        </CardHeader>
        <CardContent>
          <MetricsSummaryGrid analysis={baseAnalysis} />
        </CardContent>
      </Card>

      {/* Charts Section (if provided) */}
      {overviewMetrics && overviewMetrics.length > 0 && (
        <Card className="hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <CardTitle>Performance Metrics</CardTitle>
            </div>
            <CardDescription>
              Visual representation of analysis performance and results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MetricsGrid metrics={overviewMetrics} columns={2} compact={false} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
