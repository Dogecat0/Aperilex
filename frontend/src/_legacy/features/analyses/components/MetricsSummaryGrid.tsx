import { ArrowUpWideNarrow, Target, Brain, TrendingUp } from 'lucide-react'
import { MetricCard } from '@/components/charts/MetricCard'
import { getCoverageRating } from '@/utils/analysisMetricsUtils'
import type { AnalysisResponse } from '@/api/types'

interface MetricsSummaryGridProps {
  analysis: AnalysisResponse
}

export function MetricsSummaryGrid({ analysis }: MetricsSummaryGridProps) {
  const metrics = [
    {
      label: 'Coverage',
      value: getCoverageRating(analysis.sections_analyzed)?.label || 'N/A',
      icon: ArrowUpWideNarrow,
      color: 'text-secondary bg-primary/10',
    },
    {
      label: 'Sections Analyzed',
      value: analysis.sections_analyzed?.toString() || 'N/A',
      icon: Target,
      color: 'text-teal bg-accent/10',
    },
    {
      label: 'Key Insights',
      value: analysis.key_insights?.length.toString() || '0',
      icon: Brain,
      color: 'text-warning bg-warning/10',
    },
    {
      label: 'Risk Factors',
      value: analysis.risk_factors?.length.toString() || '0',
      icon: TrendingUp,
      color: 'text-destructive bg-destructive/10',
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
  )
}
