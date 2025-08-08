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
        color:
          'bg-primary/10 text-primary border-primary/20 dark:bg-primary/20 dark:text-primary dark:border-primary/30',
        icon: Target,
      },
      FINANCIAL_FOCUSED: {
        label: 'Financial',
        color:
          'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-400 dark:border-emerald-500/30',
        icon: TrendingUp,
      },
      RISK_FOCUSED: {
        label: 'Risk',
        color:
          'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-400 dark:border-red-500/30',
        icon: AlertTriangle,
      },
      BUSINESS_FOCUSED: {
        label: 'Business',
        color:
          'bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-500/20 dark:text-teal-400 dark:border-teal-500/30',
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
      className="block bg-card rounded-lg border border-border shadow-sm hover:shadow-md hover:border-primary/30 transition-all duration-200 group dark:bg-card dark:border-border dark:hover:border-primary/30"
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
            <p className="text-foreground/80 text-sm leading-relaxed line-clamp-3 mb-3 dark:text-foreground/80">
              {analysis.executive_summary}
            </p>
          )}

          {/* Key Metrics */}
          <div className="flex flex-wrap gap-2 mb-3">
            {analysis.sections_analyzed && (
              <div className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Target className="h-3 w-3" />
                <span>{analysis.sections_analyzed} sections</span>
              </div>
            )}
            {analysis.key_insights && analysis.key_insights.length > 0 && (
              <div className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Brain className="h-3 w-3" />
                <span>{analysis.key_insights.length} insights</span>
              </div>
            )}
          </div>

          {/* Quick Insights */}
          {analysis.key_insights && analysis.key_insights.length > 0 && (
            <div className="space-y-1">
              {analysis.key_insights.slice(0, 2).map((insight, index) => (
                <div key={index} className="flex gap-2 text-xs text-muted-foreground">
                  <div className="w-1 h-1 bg-primary rounded-full mt-1.5 flex-shrink-0"></div>
                  <span className="line-clamp-1">{insight}</span>
                </div>
              ))}
              {analysis.key_insights.length > 2 && (
                <div className="text-xs text-muted-foreground/70 pl-3">
                  +{analysis.key_insights.length - 2} more insights
                </div>
              )}
            </div>
          )}
        </div>

        {/* Metadata Footer */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-4 border-t border-border/50">
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
          <ChevronRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-primary transition-colors" />
        </div>

        {/* LLM Model Badge */}
        {analysis.llm_model && (
          <div className="mt-2 inline-flex items-center px-2 py-1 bg-muted text-muted-foreground text-xs rounded">
            <Brain className="h-3 w-3 mr-1" />
            {analysis.llm_model}
          </div>
        )}
      </div>
    </Link>
  )
}
