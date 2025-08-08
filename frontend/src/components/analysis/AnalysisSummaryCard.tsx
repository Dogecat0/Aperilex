import React from 'react'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Eye,
  BarChart3,
  Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'

interface AnalysisSummaryCardProps {
  title: string
  summary?: string
  insights?: string[]
  sentiment?: number
  metrics?: {
    totalSections: number
    significantItems: number
    categories: Record<string, number>
  }
  processingTime?: number
  className?: string
}

export function AnalysisSummaryCard({
  title,
  summary,
  insights = [],
  sentiment,
  metrics,
  processingTime,
  className = '',
}: AnalysisSummaryCardProps) {
  const getSentimentConfig = (score?: number) => {
    if (score === undefined)
      return {
        icon: Eye,
        color: 'text-muted-foreground',
        bg: 'bg-muted',
        label: 'Neutral',
        description: 'No sentiment analysis available',
      }

    if (score >= 0.8)
      return {
        icon: CheckCircle,
        color: 'text-success',
        bg: 'bg-success/10',
        label: 'Very Positive',
        description: 'Highly favorable outlook',
      }
    if (score >= 0.6)
      return {
        icon: TrendingUp,
        color: 'text-success',
        bg: 'bg-success/10',
        label: 'Positive',
        description: 'Generally favorable',
      }
    if (score >= 0.4)
      return {
        icon: Eye,
        color: 'text-muted-foreground',
        bg: 'bg-muted/50',
        label: 'Neutral',
        description: 'Balanced perspective',
      }
    if (score >= 0.2)
      return {
        icon: AlertTriangle,
        color: 'text-warning',
        bg: 'bg-warning/10',
        label: 'Cautious',
        description: 'Some concerns noted',
      }
    return {
      icon: TrendingDown,
      color: 'text-destructive',
      bg: 'bg-destructive/10',
      label: 'Negative',
      description: 'Significant challenges',
    }
  }

  const sentimentConfig = getSentimentConfig(sentiment)
  const SentimentIcon = sentimentConfig.icon

  return (
    <Card
      className={`bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20 ${className}`}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg text-foreground">{title}</CardTitle>
            <CardDescription className="text-muted-foreground mt-1">
              Section analysis overview and key findings
            </CardDescription>
          </div>

          {/* Sentiment indicator */}
          <div className={`${sentimentConfig.bg} rounded-lg p-2 flex-shrink-0`}>
            <SentimentIcon className={`h-5 w-5 ${sentimentConfig.color}`} />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Sentiment overview */}
        {sentiment !== undefined && (
          <div className="flex items-center justify-between p-3 bg-card/60 dark:bg-card/30 rounded-lg">
            <div>
              <div className="text-sm font-medium text-foreground">
                Overall Sentiment: {sentimentConfig.label}
              </div>
              <div className="text-xs text-muted-foreground">{sentimentConfig.description}</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-foreground">
                {Math.round(sentiment * 100)}%
              </div>
              <div className="text-xs text-muted-foreground">confidence</div>
            </div>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Summary</h4>
            <p className="text-sm text-foreground/80 leading-relaxed bg-card/60 dark:bg-card/30 rounded-lg p-3">
              {summary}
            </p>
          </div>
        )}

        {/* Key insights */}
        {insights.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Key Insights</h4>
            <ul className="space-y-2">
              {insights.slice(0, 3).map((insight, index) => (
                <li key={index} className="flex gap-2 text-sm text-foreground/80">
                  <div className="w-1.5 h-1.5 bg-primary rounded-full mt-2 flex-shrink-0"></div>
                  <span className="flex-1">{insight}</span>
                </li>
              ))}
              {insights.length > 3 && (
                <li className="text-xs text-muted-foreground pl-3">
                  +{insights.length - 3} more insights
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Metrics grid */}
        {metrics && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-card/60 dark:bg-card/30 rounded-lg p-3 text-center">
              <BarChart3 className="h-5 w-5 text-primary mx-auto mb-1" />
              <div className="text-lg font-bold text-foreground">{metrics.totalSections}</div>
              <div className="text-xs text-muted-foreground">Total Sections</div>
            </div>
            <div className="bg-card/60 dark:bg-card/30 rounded-lg p-3 text-center">
              <CheckCircle className="h-5 w-5 text-success mx-auto mb-1" />
              <div className="text-lg font-bold text-foreground">{metrics.significantItems}</div>
              <div className="text-xs text-muted-foreground">Key Items</div>
            </div>
          </div>
        )}

        {/* Categories breakdown */}
        {metrics?.categories && Object.keys(metrics.categories).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Content Categories</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(metrics.categories).map(([category, count]) => (
                <span
                  key={category}
                  className="inline-flex items-center px-2 py-1 bg-card/60 dark:bg-card/30 text-xs font-medium text-foreground/80 rounded-full"
                >
                  {category}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Processing time */}
        {processingTime && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-border/50">
            <Clock className="h-3 w-3" />
            <span>Processed in {processingTime}ms</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
