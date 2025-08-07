import { useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  Percent,
  Hash,
  Calculator,
  BarChart3,
  Target,
  Info,
  ChevronDown,
  ChevronUp,
  Loader2,
  Activity,
} from 'lucide-react'
import { MetricsVisualization } from '@/components/analysis/MetricsVisualization'
// Note: FinancialMetric interface defined below

export interface FinancialMetric {
  // From KeyFinancialMetric
  metric_name?: string
  current_value?: string | number | null
  previous_value?: string | number | null
  direction?: string
  percentage_change?: string | null
  explanation?: string
  significance?: string

  // Extended interface to support different metric types
  ratio_name?: string
  industry_benchmark?: number | null
  interpretation?: string
}

interface FinancialMetricsGridProps {
  metrics: FinancialMetric[]
  loading?: boolean
  title?: string
  showComparisons?: boolean
  highlightSignificant?: boolean
  maxDisplayCount?: number
  showTrendCharts?: boolean
  showSummaryChart?: boolean
  className?: string
}

type MetricType = 'currency' | 'percentage' | 'ratio' | 'number' | 'text'

interface ProcessedMetric {
  id: string
  name: string
  currentValue: string | number | null | undefined
  previousValue: string | number | null | undefined
  change?: number
  changeDirection: 'up' | 'down' | 'stable'
  changeText?: string
  type: MetricType
  significance?: 'high' | 'medium' | 'low'
  explanation?: string
  expanded?: boolean
  industryBenchmark?: number | null
  interpretation?: string
}

export function FinancialMetricsGrid({
  metrics,
  loading = false,
  title = 'Financial Metrics',
  showComparisons = true,
  highlightSignificant = true,
  maxDisplayCount,
  showTrendCharts = false,
  showSummaryChart = true,
  className = '',
}: FinancialMetricsGridProps) {
  const [expandedMetrics, setExpandedMetrics] = useState<Set<string>>(new Set())
  const [showAllMetrics, setShowAllMetrics] = useState(false)
  const [showChartView, setShowChartView] = useState(false)

  // Process and normalize metrics
  const processMetrics = (rawMetrics: FinancialMetric[]): ProcessedMetric[] => {
    return rawMetrics.map((metric, index) => {
      const name = metric.metric_name || metric.ratio_name || `Metric ${index + 1}`
      const currentValue = metric.current_value
      const previousValue = metric.previous_value

      // Determine metric type based on name and values
      const type = determineMetricType(name, currentValue)

      // Calculate change and direction
      const { change, changeDirection, changeText } = calculateChange(
        currentValue,
        previousValue,
        metric.percentage_change,
        metric.direction
      )

      // Determine significance level
      const significance = determineSignificance(change, metric.significance)

      return {
        id: `${name.replace(/\s+/g, '_')}_${index}`,
        name,
        currentValue,
        previousValue,
        change,
        changeDirection,
        changeText,
        type,
        significance,
        explanation: metric.explanation || metric.interpretation,
        industryBenchmark: metric.industry_benchmark,
        interpretation: metric.interpretation,
      }
    })
  }

  const determineMetricType = (
    name: string,
    value: string | number | null | undefined
  ): MetricType => {
    const nameLower = name.toLowerCase()

    // Check ratio first to avoid currency detection conflict with "debt"
    if (
      nameLower.includes('ratio') ||
      nameLower.includes('times') ||
      nameLower.includes('multiple')
    ) {
      return 'ratio'
    }

    if (
      nameLower.includes('margin') ||
      nameLower.includes('percentage') ||
      nameLower.includes('rate') ||
      nameLower.includes('yield') ||
      nameLower.includes('%') ||
      (typeof value === 'string' && value.includes('%'))
    ) {
      return 'percentage'
    }

    if (
      nameLower.includes('revenue') ||
      nameLower.includes('income') ||
      nameLower.includes('cash') ||
      nameLower.includes('assets') ||
      nameLower.includes('debt') ||
      nameLower.includes('$')
    ) {
      return 'currency'
    }

    if (typeof value === 'number' || (typeof value === 'string' && /^\d+\.?\d*$/.test(value))) {
      return 'number'
    }

    return 'text'
  }

  const calculateChange = (
    current: string | number | null | undefined,
    previous: string | number | null | undefined,
    percentageChange?: string | null,
    direction?: string | null
  ) => {
    let change: number | undefined
    let changeDirection: 'up' | 'down' | 'stable' = 'stable'
    let changeText: string | undefined

    // Use provided percentage change if available
    if (percentageChange) {
      const percentMatch = percentageChange.match(/(-?\d+\.?\d*)%?/)
      if (percentMatch) {
        change = parseFloat(percentMatch[1])
        changeText = percentageChange
      }
    }

    // Use direction if provided
    if (direction) {
      const directionLower = direction.toLowerCase()
      if (directionLower.includes('increase') || directionLower.includes('up')) {
        changeDirection = 'up'
      } else if (directionLower.includes('decrease') || directionLower.includes('down')) {
        changeDirection = 'down'
      }
      changeText = changeText || direction
    }

    // Calculate from numeric values if possible and no change provided
    if (!change && !changeText && current && previous) {
      const currentNum =
        typeof current === 'number' ? current : parseFloat(String(current).replace(/[^\d.-]/g, ''))
      const previousNum =
        typeof previous === 'number'
          ? previous
          : parseFloat(String(previous).replace(/[^\d.-]/g, ''))

      if (!isNaN(currentNum) && !isNaN(previousNum) && previousNum !== 0) {
        change = ((currentNum - previousNum) / Math.abs(previousNum)) * 100
        changeText = `${change > 0 ? '+' : ''}${change.toFixed(1)}%`
      }
    }

    // Determine direction from change
    if (change !== undefined) {
      changeDirection = change > 0 ? 'up' : change < 0 ? 'down' : 'stable'
    }

    return { change, changeDirection, changeText }
  }

  const determineSignificance = (
    change?: number,
    significanceText?: string
  ): 'high' | 'medium' | 'low' => {
    if (significanceText) {
      const lower = significanceText.toLowerCase()
      if (lower.includes('significant') || lower.includes('major') || lower.includes('critical')) {
        return 'high'
      }
      if (lower.includes('moderate') || lower.includes('notable')) {
        return 'medium'
      }
    }

    if (change !== undefined) {
      const absChange = Math.abs(change)
      if (absChange >= 20) return 'high'
      if (absChange >= 10) return 'medium'
    }

    return 'low'
  }

  const formatValue = (value: string | number | null | undefined, type: MetricType): string => {
    if (value === null || value === undefined) return 'N/A'

    if (typeof value === 'string') {
      // Return as-is if already formatted
      if (value.includes('$') || value.includes('%') || value === 'N/A') {
        return value
      }

      // Try to parse and format numeric strings
      const numValue = parseFloat(value.replace(/[^\d.-]/g, ''))
      if (isNaN(numValue)) return value

      value = numValue
    }

    if (typeof value !== 'number') return String(value)

    switch (type) {
      case 'currency':
        if (Math.abs(value) >= 1e12) {
          return `$${(value / 1e12).toFixed(1)}T`
        } else if (Math.abs(value) >= 1e9) {
          return `$${(value / 1e9).toFixed(1)}B`
        } else if (Math.abs(value) >= 1e6) {
          return `$${(value / 1e6).toFixed(1)}M`
        } else if (Math.abs(value) >= 1e3) {
          return `$${(value / 1e3).toFixed(1)}K`
        } else {
          return `$${value.toLocaleString()}`
        }

      case 'percentage':
        return `${value.toFixed(1)}%`

      case 'ratio':
        return value.toFixed(2)

      case 'number':
        if (Math.abs(value) >= 1e9) {
          return `${(value / 1e9).toFixed(1)}B`
        } else if (Math.abs(value) >= 1e6) {
          return `${(value / 1e6).toFixed(1)}M`
        } else if (Math.abs(value) >= 1e3) {
          return `${(value / 1e3).toFixed(1)}K`
        } else {
          return value.toLocaleString()
        }

      default:
        return String(value)
    }
  }

  const getMetricIcon = (type: MetricType) => {
    switch (type) {
      case 'currency':
        return DollarSign
      case 'percentage':
        return Percent
      case 'ratio':
        return Calculator
      default:
        return Hash
    }
  }

  const getChangeIcon = (direction: 'up' | 'down' | 'stable') => {
    switch (direction) {
      case 'up':
        return TrendingUp
      case 'down':
        return TrendingDown
      default:
        return Minus
    }
  }

  const getChangeColor = (direction: 'up' | 'down' | 'stable', significance: string) => {
    const baseColor = direction === 'up' ? 'success' : direction === 'down' ? 'error' : 'gray'
    const intensity = significance === 'high' ? '600' : significance === 'medium' ? '500' : '400'
    return `text-${baseColor}-${intensity}`
  }

  const getSignificanceBorder = (significance: 'high' | 'medium' | 'low') => {
    if (!highlightSignificant) return 'border-gray-200'

    switch (significance) {
      case 'high':
        return 'border-blue-300 ring-1 ring-blue-100'
      case 'medium':
        return 'border-blue-200'
      default:
        return 'border-gray-200'
    }
  }

  const toggleExpanded = (metricId: string) => {
    const newExpanded = new Set(expandedMetrics)
    if (newExpanded.has(metricId)) {
      newExpanded.delete(metricId)
    } else {
      newExpanded.add(metricId)
    }
    setExpandedMetrics(newExpanded)
  }

  // Generate trend data for visualizations
  const generateTrendData = (processedMetrics: ProcessedMetric[]) => {
    return processedMetrics
      .filter((m) => m.currentValue && typeof m.currentValue === 'number')
      .slice(0, 8) // Limit for readability
      .map((metric) => {
        const current = typeof metric.currentValue === 'number' ? metric.currentValue : 0
        const previous =
          typeof metric.previousValue === 'number' ? metric.previousValue : current * 0.9

        return {
          name: metric.name.length > 15 ? metric.name.substring(0, 12) + '...' : metric.name,
          current: current,
          previous: previous,
          change: metric.change || 0,
          trend: metric.changeDirection,
        }
      })
  }

  // Generate comparison chart data
  const generateComparisonData = (processedMetrics: ProcessedMetric[]) => {
    const significantMetrics = processedMetrics
      .filter((m) => m.significance === 'high' && typeof m.currentValue === 'number')
      .slice(0, 6)

    if (significantMetrics.length === 0) return []

    return significantMetrics.map((metric) => ({
      name: metric.name.length > 20 ? metric.name.substring(0, 17) + '...' : metric.name,
      value: typeof metric.currentValue === 'number' ? metric.currentValue : 0,
      trend: metric.changeDirection,
      color:
        metric.changeDirection === 'up'
          ? '#10b981'
          : metric.changeDirection === 'down'
            ? '#ef4444'
            : '#6b7280',
    }))
  }

  if (loading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Loading {title}...</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="animate-pulse">
              <div className="bg-gray-200 h-32 rounded-lg"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!metrics || metrics.length === 0) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Financial Metrics Available</h3>
        <p className="text-gray-500">
          Financial metrics will appear here when analysis data is available.
        </p>
      </div>
    )
  }

  const processedMetrics = processMetrics(metrics)
  const displayMetrics =
    maxDisplayCount && !showAllMetrics
      ? processedMetrics.slice(0, maxDisplayCount)
      : processedMetrics
  const hasMoreMetrics = maxDisplayCount && processedMetrics.length > maxDisplayCount

  const trendData = generateTrendData(processedMetrics)
  const comparisonData = generateComparisonData(processedMetrics)

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {processedMetrics.length} metrics
          </span>
        </div>

        <div className="flex items-center gap-2">
          {(showTrendCharts || showSummaryChart) && comparisonData.length > 0 && (
            <button
              onClick={() => setShowChartView(!showChartView)}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                showChartView
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Activity className="h-4 w-4" />
              {showChartView ? 'Grid View' : 'Chart View'}
            </button>
          )}

          {hasMoreMetrics && (
            <button
              onClick={() => setShowAllMetrics(!showAllMetrics)}
              className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {showAllMetrics ? (
                <>
                  Show Less <ChevronUp className="h-4 w-4" />
                </>
              ) : (
                <>
                  Show All ({processedMetrics.length}) <ChevronDown className="h-4 w-4" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Chart Views */}
      {showChartView && comparisonData.length > 0 && (
        <div className="space-y-4 bg-gray-50 rounded-lg p-4">
          {/* Key Metrics Comparison */}
          {showSummaryChart && (
            <MetricsVisualization
              title="Key Financial Metrics Comparison"
              subtitle="Significant metrics with trend indicators"
              data={comparisonData}
              chartType="bar"
              dataType="currency"
              height={250}
              showTrend={true}
            />
          )}

          {/* Trend Analysis */}
          {showTrendCharts && trendData.length > 1 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <MetricsVisualization
                title="Performance Trends"
                subtitle="Current vs previous period"
                data={trendData.map((item) => ({ name: item.name, value: item.current }))}
                chartType="line"
                dataType="currency"
                height={200}
                compact={true}
                showTrend={true}
              />

              <MetricsVisualization
                title="Change Distribution"
                subtitle="Percentage changes by metric"
                data={trendData
                  .filter((item) => item.change !== 0)
                  .map((item) => ({
                    name: item.name,
                    value: Math.abs(item.change),
                    color:
                      item.trend === 'up'
                        ? '#10b981'
                        : item.trend === 'down'
                          ? '#ef4444'
                          : '#6b7280',
                  }))}
                chartType="bar"
                dataType="percentage"
                height={200}
                compact={true}
              />
            </div>
          )}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {displayMetrics.map((metric) => {
          const Icon = getMetricIcon(metric.type)
          const ChangeIcon = getChangeIcon(metric.changeDirection)
          const isExpanded = expandedMetrics.has(metric.id)
          const hasDetailedInfo =
            metric.explanation || metric.interpretation || metric.industryBenchmark

          return (
            <div
              key={metric.id}
              className={`bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border ${getSignificanceBorder(
                metric.significance || 'low'
              )}`}
            >
              {/* Main Content */}
              <div className="p-4">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="bg-blue-50 p-2 rounded-lg">
                      <Icon className="h-4 w-4 text-blue-600" />
                    </div>
                    <h4 className="font-medium text-gray-900 truncate" title={metric.name}>
                      {metric.name}
                    </h4>
                  </div>

                  {metric.significance === 'high' && (
                    <div className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
                      Key
                    </div>
                  )}
                </div>

                {/* Current Value */}
                <div className="mb-2">
                  <div className="flex items-end justify-between">
                    <p className="text-2xl font-bold text-gray-900">
                      {formatValue(metric.currentValue, metric.type)}
                    </p>

                    {/* Mini sparkline for trend visualization */}
                    {showTrendCharts &&
                      metric.previousValue &&
                      metric.currentValue &&
                      typeof metric.currentValue === 'number' &&
                      typeof metric.previousValue === 'number' && (
                        <div className="flex items-end h-8 w-16">
                          <MetricsVisualization
                            title=""
                            data={[
                              { name: 'Prev', value: metric.previousValue },
                              { name: 'Curr', value: metric.currentValue },
                            ]}
                            chartType="line"
                            dataType={metric.type}
                            height={32}
                            compact={true}
                            showLegend={false}
                            showGrid={false}
                            className="sparkline"
                          />
                        </div>
                      )}
                  </div>
                </div>

                {/* Previous Value & Change */}
                {showComparisons && (metric.previousValue || metric.changeText) && (
                  <div className="space-y-1 mb-3">
                    {metric.previousValue && (
                      <p className="text-sm text-gray-500">
                        Previous: {formatValue(metric.previousValue, metric.type)}
                      </p>
                    )}

                    {metric.changeText && (
                      <div
                        className={`flex items-center gap-1 text-sm ${getChangeColor(
                          metric.changeDirection,
                          metric.significance || 'low'
                        )}`}
                      >
                        <ChangeIcon className="h-3 w-3" />
                        <span className="font-medium">{metric.changeText}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Industry Benchmark */}
                {metric.industryBenchmark && (
                  <div className="text-sm text-gray-600 mb-2">
                    <span className="font-medium">Industry avg:</span>{' '}
                    {formatValue(metric.industryBenchmark, metric.type)}
                  </div>
                )}

                {/* Expand Button */}
                {hasDetailedInfo && (
                  <button
                    onClick={() => toggleExpanded(metric.id)}
                    className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium mt-2"
                  >
                    <Info className="h-3 w-3" />
                    {isExpanded ? 'Less Info' : 'More Info'}
                    {isExpanded ? (
                      <ChevronUp className="h-3 w-3" />
                    ) : (
                      <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                )}
              </div>

              {/* Expanded Details */}
              {isExpanded && hasDetailedInfo && (
                <div className="border-t border-gray-100 p-4 bg-gray-50">
                  {metric.explanation && (
                    <div className="mb-3">
                      <h5 className="font-medium text-gray-900 mb-1 text-sm">Explanation</h5>
                      <p className="text-sm text-gray-700 leading-relaxed">{metric.explanation}</p>
                    </div>
                  )}

                  {metric.interpretation && metric.interpretation !== metric.explanation && (
                    <div>
                      <h5 className="font-medium text-gray-900 mb-1 text-sm">Interpretation</h5>
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {metric.interpretation}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Show More/Less Toggle */}
      {hasMoreMetrics && displayMetrics.length < processedMetrics.length && (
        <div className="text-center">
          <button
            onClick={() => setShowAllMetrics(true)}
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            Show {processedMetrics.length - displayMetrics.length} more metrics
          </button>
        </div>
      )}

      {/* Debug Info (Development) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="mt-4">
          <summary className="text-xs text-gray-500 cursor-pointer">
            Debug: Processed Metrics
          </summary>
          <pre className="text-xs text-gray-600 bg-gray-100 p-2 rounded mt-1 overflow-auto">
            {JSON.stringify(processedMetrics.slice(0, 2), null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}

// Re-export types for external use
export type { ProcessedMetric, MetricType }
