import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  DollarSign,
  Target,
  Info,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
} from 'lucide-react'

export type InsightType = 'financial' | 'risk' | 'opportunity' | 'general'
export type InsightPriority = 'low' | 'medium' | 'high' | 'critical'

interface InsightHighlightProps {
  text: string
  type?: InsightType
  priority?: InsightPriority
  sentiment?: 'positive' | 'negative' | 'neutral'
  className?: string
  showPriorityIndicator?: boolean
  compact?: boolean
}

export function InsightHighlight({
  text,
  type = 'general',
  priority = 'medium',
  sentiment,
  className = '',
  showPriorityIndicator = true,
  compact = false,
}: InsightHighlightProps) {
  // Get type configuration
  const getTypeConfig = (insightType: InsightType) => {
    switch (insightType) {
      case 'financial':
        return {
          icon: DollarSign,
          gradient: 'bg-primary/5',
          borderColor: 'border-primary/20',
          iconColor: 'text-primary',
          iconBg: 'bg-primary/10',
          accentColor: 'text-primary',
        }
      case 'risk':
        return {
          icon: AlertTriangle,
          gradient: 'bg-destructive/5',
          borderColor: 'border-destructive/20',
          iconColor: 'text-destructive',
          iconBg: 'bg-destructive/10',
          accentColor: 'text-destructive',
        }
      case 'opportunity':
        return {
          icon: Target,
          gradient: 'bg-success/5',
          borderColor: 'border-success/20',
          iconColor: 'text-success',
          iconBg: 'bg-success/10',
          accentColor: 'text-success',
        }
      default: // general
        return {
          icon: Info,
          gradient: 'bg-gradient-to-r from-muted/50 to-muted/30',
          borderColor: 'border-border',
          iconColor: 'text-muted-foreground',
          iconBg: 'bg-muted/50',
          accentColor: 'text-muted-foreground',
        }
    }
  }

  // Get priority configuration
  const getPriorityConfig = (priorityLevel: InsightPriority) => {
    switch (priorityLevel) {
      case 'critical':
        return {
          dot: 'bg-destructive',
          pulse: 'animate-pulse',
          label: 'Critical',
          labelColor: 'text-destructive',
          labelBg: 'bg-destructive/10',
          weight: 4,
        }
      case 'high':
        return {
          dot: 'bg-orange-500',
          pulse: '',
          label: 'High Priority',
          labelColor: 'text-orange-500',
          labelBg: 'bg-orange-500/10',
          weight: 3,
        }
      case 'medium':
        return {
          dot: 'bg-yellow-500',
          pulse: '',
          label: 'Medium',
          labelColor: 'text-yellow-500',
          labelBg: 'bg-yellow-500/10',
          weight: 2,
        }
      case 'low':
        return {
          dot: 'bg-muted-foreground/50',
          pulse: '',
          label: 'Low Priority',
          labelColor: 'text-muted-foreground',
          labelBg: 'bg-muted/50',
          weight: 1,
        }
    }
  }

  // Get sentiment configuration (overrides type if specified)
  const getSentimentConfig = (sentimentType?: string) => {
    if (!sentimentType) return null

    switch (sentimentType) {
      case 'positive':
        return {
          icon: TrendingUp,
          iconColor: 'text-success',
          iconBg: 'bg-success/10',
          gradient: 'bg-success/5',
          borderColor: 'border-success/20',
        }
      case 'negative':
        return {
          icon: TrendingDown,
          iconColor: 'text-destructive',
          iconBg: 'bg-destructive/10',
          gradient: 'bg-destructive/5',
          borderColor: 'border-destructive/20',
        }
      case 'neutral':
      default:
        return {
          icon: BarChart3,
          iconColor: 'text-muted-foreground',
          iconBg: 'bg-muted/50',
          gradient: 'bg-gradient-to-r from-muted/50 to-muted/30',
          borderColor: 'border-border',
        }
    }
  }

  const typeConfig = getTypeConfig(type)
  const priorityConfig = getPriorityConfig(priority)
  const sentimentConfig = getSentimentConfig(sentiment)

  // Use sentiment config if available, otherwise use type config
  const finalConfig = sentimentConfig ? { ...typeConfig, ...sentimentConfig } : typeConfig
  const FinalIcon = finalConfig.icon

  return (
    <div
      className={`rounded-lg border ${finalConfig.borderColor} ${finalConfig.gradient} shadow-sm hover:shadow-md transition-all duration-200 ${className}`}
    >
      <div className={`${compact ? 'p-3' : 'p-4'}`}>
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`${finalConfig.iconBg} rounded-lg p-2 flex-shrink-0`}>
            <FinalIcon className={`${compact ? 'h-3 w-3' : 'h-4 w-4'} ${finalConfig.iconColor}`} />
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            {/* Priority indicator and type badge */}
            {showPriorityIndicator && !compact && (
              <div className="flex items-center gap-2 mb-2">
                <div className="flex items-center gap-1.5">
                  <div
                    className={`w-2 h-2 rounded-full ${priorityConfig.dot} ${priorityConfig.pulse}`}
                  ></div>
                  <span className={`text-xs font-medium ${priorityConfig.labelColor}`}>
                    {priorityConfig.label}
                  </span>
                </div>

                {/* Type badge */}
                <div
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${priorityConfig.labelBg} ${priorityConfig.labelColor}`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </div>
              </div>
            )}

            {/* Insight text */}
            <p
              className={`${compact ? 'text-sm' : 'text-sm'} text-foreground/90 leading-relaxed ${compact ? 'line-clamp-2' : ''}`}
            >
              {text}
            </p>

            {/* Priority indicator for compact mode */}
            {showPriorityIndicator && compact && (
              <div className="flex items-center gap-2 mt-2">
                <div
                  className={`w-1.5 h-1.5 rounded-full ${priorityConfig.dot} ${priorityConfig.pulse}`}
                ></div>
                <span className="text-xs text-muted-foreground">
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </span>
                <span className="text-xs text-muted-foreground/50">"</span>
                <span className={`text-xs ${priorityConfig.labelColor}`}>
                  {priorityConfig.label}
                </span>
              </div>
            )}
          </div>

          {/* Sentiment/status indicator */}
          {sentiment && (
            <div className="flex-shrink-0">
              {sentiment === 'positive' && <CheckCircle className="h-4 w-4 text-success" />}
              {sentiment === 'negative' && <XCircle className="h-4 w-4 text-destructive" />}
              {sentiment === 'neutral' && <Clock className="h-4 w-4 text-muted-foreground" />}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper component for rendering multiple insights with proper spacing
interface InsightGroupProps {
  insights: Array<{
    text: string
    type?: InsightType
    priority?: InsightPriority
    sentiment?: 'positive' | 'negative' | 'neutral'
  }>
  title?: string
  className?: string
  compact?: boolean
  maxItems?: number
}

export function InsightGroup({
  insights,
  title,
  className = '',
  compact = false,
  maxItems,
}: InsightGroupProps) {
  const displayInsights = maxItems ? insights.slice(0, maxItems) : insights
  const hasMore = maxItems && insights.length > maxItems

  // Sort by priority (critical -> high -> medium -> low)
  const sortedInsights = [...displayInsights].sort((a, b) => {
    const priorityWeights = { critical: 4, high: 3, medium: 2, low: 1 }
    const aPriority = priorityWeights[a.priority || 'medium']
    const bPriority = priorityWeights[b.priority || 'medium']
    return bPriority - aPriority
  })

  return (
    <div className={className}>
      {title && (
        <h4
          className={`font-semibold text-foreground ${compact ? 'text-sm mb-2' : 'text-base mb-3'}`}
        >
          {title}
          {insights.length > 0 && (
            <span className="text-muted-foreground font-normal text-sm ml-2">
              ({insights.length})
            </span>
          )}
        </h4>
      )}

      <div className={`space-y-${compact ? '2' : '3'}`}>
        {sortedInsights.map((insight, index) => (
          <InsightHighlight
            key={index}
            text={insight.text}
            type={insight.type}
            priority={insight.priority}
            sentiment={insight.sentiment}
            compact={compact}
          />
        ))}

        {hasMore && (
          <div className="text-center py-2">
            <span className="text-sm text-muted-foreground">
              +{insights.length - maxItems!} more insights
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
