import { Link } from 'react-router-dom'
import {
  Calendar,
  Clock,
  TrendingUp,
  AlertTriangle,
  Target,
  Brain,
  ChevronRight,
} from 'lucide-react'
import { ConfidenceIndicator } from './ConfidenceIndicator'
import type { AnalysisResponse } from '@/api/types'

interface AnalysisCardProps {
  analysis: AnalysisResponse
}

export function AnalysisCard({ analysis }: AnalysisCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getAnalysisTypeConfig = (type: string) => {
    const configs = {
      COMPREHENSIVE: {
        label: 'Comprehensive',
        color: 'bg-primary-100 text-primary-800 border-primary-200',
        icon: Target,
      },
      FINANCIAL_FOCUSED: {
        label: 'Financial',
        color: 'bg-success-100 text-success-800 border-success-200',
        icon: TrendingUp,
      },
      RISK_FOCUSED: {
        label: 'Risk',
        color: 'bg-error-100 text-error-800 border-error-200',
        icon: AlertTriangle,
      },
      BUSINESS_FOCUSED: {
        label: 'Business',
        color: 'bg-teal-100 text-teal-800 border-teal-200',
        icon: Brain,
      },
    }
    return configs[type as keyof typeof configs] || configs.COMPREHENSIVE
  }

  const typeConfig = getAnalysisTypeConfig(analysis.analysis_type)
  const TypeIcon = typeConfig.icon

  return (
    <Link
      to={`/analyses/${analysis.analysis_id}`}
      className="block bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-primary-200 transition-all duration-200 group"
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${typeConfig.color}`}
            >
              <TypeIcon className="h-3 w-3" />
              {typeConfig.label}
            </div>
          </div>
          <ConfidenceIndicator score={analysis.confidence_score} size="sm" />
        </div>

        {/* Content Preview */}
        <div className="mb-4">
          {analysis.executive_summary && (
            <p className="text-gray-700 text-sm leading-relaxed line-clamp-3 mb-3">
              {analysis.executive_summary}
            </p>
          )}

          {/* Key Metrics */}
          <div className="flex flex-wrap gap-2 mb-3">
            {analysis.sections_analyzed && (
              <div className="inline-flex items-center gap-1 text-xs text-gray-600">
                <Target className="h-3 w-3" />
                <span>{analysis.sections_analyzed} sections</span>
              </div>
            )}
            {analysis.key_insights && analysis.key_insights.length > 0 && (
              <div className="inline-flex items-center gap-1 text-xs text-gray-600">
                <Brain className="h-3 w-3" />
                <span>{analysis.key_insights.length} insights</span>
              </div>
            )}
          </div>

          {/* Quick Insights */}
          {analysis.key_insights && analysis.key_insights.length > 0 && (
            <div className="space-y-1">
              {analysis.key_insights.slice(0, 2).map((insight, index) => (
                <div key={index} className="flex gap-2 text-xs text-gray-600">
                  <div className="w-1 h-1 bg-primary-500 rounded-full mt-1.5 flex-shrink-0"></div>
                  <span className="line-clamp-1">{insight}</span>
                </div>
              ))}
              {analysis.key_insights.length > 2 && (
                <div className="text-xs text-gray-500 pl-3">
                  +{analysis.key_insights.length - 2} more insights
                </div>
              )}
            </div>
          )}
        </div>

        {/* Metadata Footer */}
        <div className="flex items-center justify-between text-xs text-gray-500 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{formatDate(analysis.created_at)}</span>
            </div>
            {analysis.processing_time_seconds && (
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{analysis.processing_time_seconds}s</span>
              </div>
            )}
          </div>
          <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-primary-500 transition-colors" />
        </div>

        {/* LLM Model Badge */}
        {analysis.llm_model && (
          <div className="mt-2 inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
            <Brain className="h-3 w-3 mr-1" />
            {analysis.llm_model}
          </div>
        )}
      </div>
    </Link>
  )
}
