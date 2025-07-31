import React from 'react'
import { Button } from '@/components/ui/Button'
import {
  BarChart3,
  Brain,
  TrendingUp,
  AlertTriangle,
  Target,
  DollarSign,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
  Eye,
} from 'lucide-react'
import type { AnalysisResponse } from '@/api/types'

interface FilingAnalysisSectionProps {
  analysis: AnalysisResponse | null
  isLoading: boolean
  error: any
  onAnalyze?: () => void
  onViewFullAnalysis?: () => void
  isAnalyzing?: boolean
}

export const FilingAnalysisSection: React.FC<FilingAnalysisSectionProps> = ({
  analysis,
  isLoading,
  error,
  onAnalyze,
  onViewFullAnalysis,
  isAnalyzing = false,
}) => {
  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <BarChart3 className="w-5 h-5" />
          <span>Analysis Results</span>
        </h3>
        <div className="space-y-4">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-20 bg-gray-200 rounded mb-4"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="h-16 bg-gray-200 rounded"></div>
              <div className="h-16 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error && !analysis) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <BarChart3 className="w-5 h-5" />
          <span>Analysis Results</span>
        </h3>
        <div className="text-center py-8">
          <XCircle className="mx-auto w-12 h-12 text-red-500 mb-4" />
          <h4 className="text-lg font-medium text-foreground mb-2">Analysis Error</h4>
          <p className="text-sm text-muted-foreground mb-4">
            There was an error loading the analysis for this filing.
          </p>
          {onAnalyze && (
            <Button onClick={onAnalyze} disabled={isAnalyzing}>
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry Analysis
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <BarChart3 className="w-5 h-5" />
          <span>Analysis Results</span>
        </h3>
        <div className="text-center py-8">
          <Brain className="mx-auto w-12 h-12 text-muted-foreground mb-4" />
          <h4 className="text-lg font-medium text-foreground mb-2">No Analysis Available</h4>
          <p className="text-sm text-muted-foreground mb-4">
            This filing hasn't been analyzed yet. Start an AI-powered analysis to extract key
            insights.
          </p>
          {onAnalyze && (
            <Button onClick={onAnalyze} disabled={isAnalyzing}>
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4 mr-2" />
                  Start Analysis
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center space-x-2">
          <BarChart3 className="w-5 h-5" />
          <span>Analysis Results</span>
        </h3>
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2 py-1 rounded-md bg-green-100 text-green-800 text-xs font-medium">
            <CheckCircle className="w-3 h-3 mr-1" />
            Complete
          </span>
          {onViewFullAnalysis && (
            <Button variant="outline" size="sm" onClick={onViewFullAnalysis}>
              <Eye className="w-4 h-4 mr-2" />
              View Full Analysis
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {/* Executive Summary */}
        {analysis.executive_summary && (
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2 flex items-center space-x-2">
              <Brain className="w-4 h-4" />
              <span>Executive Summary</span>
            </h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {analysis.executive_summary}
            </p>
          </div>
        )}

        {/* Key Insights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Key Insights */}
          {analysis.key_insights && analysis.key_insights.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <h5 className="text-sm font-medium">Key Insights</h5>
              </div>
              <div className="space-y-1">
                {analysis.key_insights.slice(0, 3).map((insight, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <div className="w-1 h-1 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground line-clamp-2">{insight}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Financial Highlights */}
          {analysis.financial_highlights && analysis.financial_highlights.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <DollarSign className="w-4 h-4 text-green-600" />
                <h5 className="text-sm font-medium">Financial Highlights</h5>
              </div>
              <div className="space-y-1">
                {analysis.financial_highlights.slice(0, 3).map((highlight, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <div className="w-1 h-1 bg-green-600 rounded-full mt-2 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground line-clamp-2">{highlight}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {analysis.risk_factors && analysis.risk_factors.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-yellow-600" />
                <h5 className="text-sm font-medium">Risk Factors</h5>
              </div>
              <div className="space-y-1">
                {analysis.risk_factors.slice(0, 3).map((risk, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <div className="w-1 h-1 bg-yellow-600 rounded-full mt-2 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground line-clamp-2">{risk}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Opportunities */}
          {analysis.opportunities && analysis.opportunities.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Target className="w-4 h-4 text-purple-600" />
                <h5 className="text-sm font-medium">Opportunities</h5>
              </div>
              <div className="space-y-1">
                {analysis.opportunities.slice(0, 3).map((opportunity, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <div className="w-1 h-1 bg-purple-600 rounded-full mt-2 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground line-clamp-2">{opportunity}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Analysis Metadata */}
        <div className="pt-4 border-t">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Analysis Type</p>
              <p className="font-medium">{analysis.analysis_type}</p>
            </div>
            {analysis.confidence_score && (
              <div>
                <p className="text-muted-foreground">Confidence Score</p>
                <p className="font-medium">{Math.round(analysis.confidence_score * 100)}%</p>
              </div>
            )}
            {analysis.sections_analyzed && (
              <div>
                <p className="text-muted-foreground">Sections Analyzed</p>
                <p className="font-medium">{analysis.sections_analyzed}</p>
              </div>
            )}
            <div>
              <p className="text-muted-foreground">Created</p>
              <p className="font-medium">{new Date(analysis.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          {analysis.processing_time_seconds && (
            <div className="mt-3 flex items-center space-x-2 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              <span>Processing time: {analysis.processing_time_seconds}s</span>
              {analysis.llm_provider && <span>• Provider: {analysis.llm_provider}</span>}
              {analysis.llm_model && <span>• Model: {analysis.llm_model}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
