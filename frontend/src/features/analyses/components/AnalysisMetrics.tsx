import { Clock, Target, Brain, TrendingUp, FileText, Zap, ChevronRight } from 'lucide-react'
import { MetricCard } from '@/components/charts/MetricCard'
import { ConfidenceIndicator } from './ConfidenceIndicator'
import type { AnalysisResponse } from '@/api/types'

interface AnalysisMetricsProps {
  analysis: AnalysisResponse
}

export function AnalysisMetrics({ analysis }: AnalysisMetricsProps) {
  const formatProcessingTime = (seconds?: number | null) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  const getAnalysisTypeColor = (type: string) => {
    const colors = {
      COMPREHENSIVE: 'text-primary-600 bg-primary-50',
      FINANCIAL_FOCUSED: 'text-success-600 bg-success-50',
      RISK_FOCUSED: 'text-error-600 bg-error-50',
      BUSINESS_FOCUSED: 'text-teal-600 bg-teal-50',
    }
    return colors[type as keyof typeof colors] || 'text-gray-600 bg-gray-50'
  }

  const metrics = [
    {
      label: 'Processing Time',
      value: formatProcessingTime(analysis.processing_time_seconds),
      icon: Clock,
      color: 'text-blue-600 bg-blue-50',
    },
    {
      label: 'Sections Analyzed',
      value: analysis.sections_analyzed?.toString() || 'N/A',
      icon: Target,
      color: 'text-purple-600 bg-purple-50',
    },
    {
      label: 'Key Insights',
      value: analysis.key_insights?.length.toString() || '0',
      icon: Brain,
      color: 'text-amber-600 bg-amber-50',
    },
    {
      label: 'Risk Factors',
      value: analysis.risk_factors?.length.toString() || '0',
      icon: TrendingUp,
      color: 'text-red-600 bg-red-50',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Analysis Overview */}
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Overview</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Analysis Type</span>
            <div
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getAnalysisTypeColor(analysis.analysis_type)}`}
            >
              {analysis.analysis_type
                .replace('_', ' ')
                .toLowerCase()
                .replace(/\b\w/g, (l) => l.toUpperCase())}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Confidence Score</span>
            <ConfidenceIndicator score={analysis.confidence_score} showLabel />
          </div>

          {analysis.llm_provider && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">LLM Provider</span>
              <span className="text-sm text-gray-600">{analysis.llm_provider}</span>
            </div>
          )}

          {analysis.llm_model && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Model</span>
              <span className="text-sm text-gray-600 font-mono">{analysis.llm_model}</span>
            </div>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Metrics</h3>
        <div className="space-y-3">
          {metrics.map((metric) => (
            <MetricCard
              key={metric.label}
              label={metric.label}
              value={metric.value}
              icon={metric.icon}
              iconColor={metric.color}
              size="sm"
            />
          ))}
        </div>
      </div>

      {/* Performance Indicators */}
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>

        <div className="space-y-3">
          {/* Processing Speed Indicator */}
          {analysis.processing_time_seconds && (
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-600" />
                <span className="text-sm font-medium text-gray-700">Processing Speed</span>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    analysis.processing_time_seconds < 30
                      ? 'bg-success-500'
                      : analysis.processing_time_seconds < 60
                        ? 'bg-warning-500'
                        : 'bg-error-500'
                  }`}
                ></div>
                <span className="text-sm text-gray-600">
                  {analysis.processing_time_seconds < 30
                    ? 'Fast'
                    : analysis.processing_time_seconds < 60
                      ? 'Medium'
                      : 'Slow'}
                </span>
              </div>
            </div>
          )}

          {/* Comprehensiveness Indicator */}
          {analysis.sections_analyzed && (
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium text-gray-700">Coverage</span>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    analysis.sections_analyzed >= 5
                      ? 'bg-success-500'
                      : analysis.sections_analyzed >= 3
                        ? 'bg-warning-500'
                        : 'bg-error-500'
                  }`}
                ></div>
                <span className="text-sm text-gray-600">
                  {analysis.sections_analyzed >= 5
                    ? 'Comprehensive'
                    : analysis.sections_analyzed >= 3
                      ? 'Moderate'
                      : 'Limited'}
                </span>
              </div>
            </div>
          )}

          {/* Insight Density */}
          {analysis.key_insights && analysis.sections_analyzed && (
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium text-gray-700">Insight Density</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  {(analysis.key_insights.length / analysis.sections_analyzed).toFixed(1)} per
                  section
                </span>
                <ChevronRight className="h-3 w-3 text-gray-400" />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Analysis Quality Score */}
      {analysis.confidence_score && (
        <div className="bg-white rounded-lg border shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quality Assessment</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Overall Quality</span>
              <span
                className={`text-sm font-medium ${
                  analysis.confidence_score >= 0.8
                    ? 'text-success-600'
                    : analysis.confidence_score >= 0.6
                      ? 'text-warning-600'
                      : 'text-error-600'
                }`}
              >
                {analysis.confidence_score >= 0.8
                  ? 'Excellent'
                  : analysis.confidence_score >= 0.6
                    ? 'Good'
                    : 'Fair'}
              </span>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  analysis.confidence_score >= 0.8
                    ? 'bg-success-500'
                    : analysis.confidence_score >= 0.6
                      ? 'bg-warning-500'
                      : 'bg-error-500'
                }`}
                style={{ width: `${(analysis.confidence_score || 0) * 100}%` }}
              ></div>
            </div>

            <p className="text-xs text-gray-500">
              Based on confidence score and analysis completeness
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
