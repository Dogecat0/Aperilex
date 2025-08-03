import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Clock,
  User,
  Target,
  Brain,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  Building,
  Calendar,
  Download,
  Share2,
} from 'lucide-react'
import { useAnalysis } from '@/hooks/useAnalysis'
import { Button } from '@/components/ui/Button'
import { AnalysisViewer } from './components/AnalysisViewer'
import { AnalysisMetrics } from './components/AnalysisMetrics'
import { ConfidenceIndicator } from './components/ConfidenceIndicator'
import { SectionResults } from './components/SectionResults'
import type { ComprehensiveAnalysisResponse } from '@/api/types'

export function AnalysisDetails() {
  const { analysisId } = useParams<{ analysisId: string }>()
  const { data: analysis, isLoading, error } = useAnalysis(analysisId!)

  if (!analysisId) {
    return (
      <div className="p-6">
        <div className="bg-error-50 border border-error-200 rounded-lg p-4">
          <h3 className="text-error-800 font-medium">Invalid Analysis ID</h3>
          <p className="text-error-600 text-sm mt-1">The analysis ID is missing from the URL.</p>
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

  // Check if this is a comprehensive analysis with full results
  const comprehensiveAnalysis = analysis.full_results as ComprehensiveAnalysisResponse | undefined
  const hasFullResults = Boolean(comprehensiveAnalysis)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getAnalysisTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      COMPREHENSIVE: 'Comprehensive Analysis',
      FINANCIAL_FOCUSED: 'Financial Analysis',
      RISK_FOCUSED: 'Risk Analysis',
      BUSINESS_FOCUSED: 'Business Analysis',
    }
    return labels[type] || type
  }

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
              <h1 className="text-2xl font-bold text-gray-900">
                {getAnalysisTypeLabel(analysis.analysis_type)}
              </h1>
              <ConfidenceIndicator score={analysis.confidence_score} />
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>{formatDate(analysis.created_at)}</span>
              </div>
              {analysis.created_by && (
                <div className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  <span>Created by {analysis.created_by}</span>
                </div>
              )}
              {analysis.processing_time_seconds && (
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  <span>Processed in {analysis.processing_time_seconds}s</span>
                </div>
              )}
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

          {/* Key Insights */}
          {analysis.key_insights && analysis.key_insights.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="h-5 w-5 text-amber-600" />
                <h2 className="text-xl font-semibold text-gray-900">Key Insights</h2>
              </div>
              <ul className="space-y-3">
                {analysis.key_insights.map((insight, index) => (
                  <li key={index} className="flex gap-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-amber-100 rounded-full flex items-center justify-center text-amber-700 text-sm font-medium">
                      {index + 1}
                    </div>
                    <p className="text-gray-700 leading-relaxed">{insight}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Comprehensive Analysis Sections */}
          {hasFullResults && comprehensiveAnalysis && (
            <SectionResults sections={comprehensiveAnalysis.section_analyses} />
          )}

          {/* Analysis Viewer for Legacy Format */}
          {!hasFullResults && analysis.full_results && (
            <AnalysisViewer results={analysis.full_results} />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Analysis Metrics */}
          <AnalysisMetrics analysis={analysis} />

          {/* Financial Highlights */}
          {analysis.financial_highlights && analysis.financial_highlights.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="h-5 w-5 text-success-600" />
                <h3 className="text-lg font-semibold text-gray-900">Financial Highlights</h3>
              </div>
              <ul className="space-y-2">
                {analysis.financial_highlights.map((highlight, index) => (
                  <li key={index} className="text-sm text-gray-700 flex gap-2">
                    <div className="w-1.5 h-1.5 bg-success-600 rounded-full mt-2 flex-shrink-0"></div>
                    <span>{highlight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risk Factors */}
          {analysis.risk_factors && analysis.risk_factors.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-5 w-5 text-error-600" />
                <h3 className="text-lg font-semibold text-gray-900">Risk Factors</h3>
              </div>
              <ul className="space-y-2">
                {analysis.risk_factors.map((risk, index) => (
                  <li key={index} className="text-sm text-gray-700 flex gap-2">
                    <div className="w-1.5 h-1.5 bg-error-600 rounded-full mt-2 flex-shrink-0"></div>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Opportunities */}
          {analysis.opportunities && analysis.opportunities.length > 0 && (
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="h-5 w-5 text-teal-600" />
                <h3 className="text-lg font-semibold text-gray-900">Opportunities</h3>
              </div>
              <ul className="space-y-2">
                {analysis.opportunities.map((opportunity, index) => (
                  <li key={index} className="text-sm text-gray-700 flex gap-2">
                    <div className="w-1.5 h-1.5 bg-teal-600 rounded-full mt-2 flex-shrink-0"></div>
                    <span>{opportunity}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
