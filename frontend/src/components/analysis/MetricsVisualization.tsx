import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Info,
} from 'lucide-react'

export type ChartType = 'line' | 'bar' | 'pie' | 'area'
export type DataType = 'currency' | 'percentage' | 'number' | 'ratio'

interface DataPoint {
  name: string
  value: number | string
  label?: string
  color?: string
  trend?: 'up' | 'down' | 'stable'
  metadata?: Record<string, any>
}

interface MetricsVisualizationProps {
  title: string
  subtitle?: string
  data: DataPoint[]
  chartType: ChartType
  dataType?: DataType
  height?: number
  showLegend?: boolean
  showGrid?: boolean
  showTrend?: boolean
  colors?: string[]
  className?: string
  compact?: boolean
}

export function MetricsVisualization({
  title,
  subtitle,
  data,
  chartType,
  dataType = 'number',
  height = 300,
  showLegend = true,
  showGrid = true,
  showTrend = false,
  colors,
  className = '',
  compact = false,
}: MetricsVisualizationProps) {
  // Default color palette from Tailwind theme
  const defaultColors = [
    '#6366f1', // primary
    '#14b8a6', // teal
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316', // orange
    '#ec4899', // pink
    '#64748b', // slate
  ]

  const chartColors = colors || defaultColors

  // Format values based on data type
  const formatValue = (value: number | string): string => {
    if (typeof value === 'string') return value

    switch (dataType) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(value)
      case 'percentage':
        return `${value.toFixed(1)}%`
      case 'ratio':
        return value.toFixed(2)
      case 'number':
      default:
        return value.toLocaleString()
    }
  }

  // Format axis labels
  const formatAxisLabel = (value: any) => {
    if (typeof value === 'number') {
      switch (dataType) {
        case 'currency':
          if (value >= 1000000000) return `$${(value / 1000000000).toFixed(1)}B`
          if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
          if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`
          return `$${value}`
        case 'percentage':
          return `${value}%`
        default:
          if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
          if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
          return value.toString()
      }
    }
    return value
  }

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 text-sm mb-2">{label}</p>
          {payload.map((item: any, index: number) => (
            <div key={index} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-sm text-gray-700">
                {item.name}: {formatValue(item.value)}
              </span>
              {data.trend && (
                <div className="flex items-center gap-1">
                  {data.trend === 'up' && <TrendingUp className="h-3 w-3 text-green-500" />}
                  {data.trend === 'down' && <TrendingDown className="h-3 w-3 text-red-500" />}
                  {data.trend === 'stable' && <Activity className="h-3 w-3 text-gray-500" />}
                </div>
              )}
            </div>
          ))}
          {data.metadata && (
            <div className="mt-2 pt-2 border-t border-gray-100">
              {Object.entries(data.metadata).map(([key, value]) => (
                <p key={key} className="text-xs text-gray-500">
                  {key}: {String(value)}
                </p>
              ))}
            </div>
          )}
        </div>
      )
    }
    return null
  }

  // Get chart icon based on type
  const getChartIcon = () => {
    switch (chartType) {
      case 'line':
        return TrendingUp
      case 'bar':
        return BarChart3
      case 'pie':
        return PieChartIcon
      case 'area':
        return Activity
      default:
        return BarChart3
    }
  }

  const ChartIcon = getChartIcon()

  // Calculate trend summary if enabled
  const getTrendSummary = () => {
    if (!showTrend || data.length < 2) return null

    const hasNumericValues = data.every((d) => typeof d.value === 'number')
    if (!hasNumericValues) return null

    const numericData = data.filter((d) => typeof d.value === 'number') as Array<
      DataPoint & { value: number }
    >
    const firstValue = numericData[0].value
    const lastValue = numericData[numericData.length - 1].value
    const change = lastValue - firstValue
    const changePercent = (change / firstValue) * 100

    return {
      change,
      changePercent,
      direction: change > 0 ? 'up' : change < 0 ? 'down' : 'stable',
      firstValue,
      lastValue,
    }
  }

  const trendSummary = getTrendSummary()

  // Render the appropriate chart
  const renderChart = () => {
    const commonProps = {
      data,
      margin: compact
        ? { top: 5, right: 5, left: 5, bottom: 5 }
        : { top: 5, right: 30, left: 20, bottom: 5 },
    }

    switch (chartType) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey="name" tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <YAxis tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey="value"
              stroke={chartColors[0]}
              strokeWidth={2}
              dot={{ r: compact ? 3 : 4 }}
            />
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey="name" tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <YAxis tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Area
              type="monotone"
              dataKey="value"
              stroke={chartColors[0]}
              fill={chartColors[0]}
              fillOpacity={0.3}
            />
          </AreaChart>
        )

      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey="name" tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <YAxis tickFormatter={formatAxisLabel} fontSize={compact ? 10 : 12} />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color || chartColors[index % chartColors.length]}
                />
              ))}
            </Bar>
          </BarChart>
        )

      case 'pie':
        return (
          <PieChart {...commonProps}>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={compact ? 60 : 80}
              fill="#8884d8"
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color || chartColors[index % chartColors.length]}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
          </PieChart>
        )

      default:
        return null
    }
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${className}`}>
      {/* Header */}
      <div className={`${compact ? 'p-3' : 'p-4'} border-b border-gray-100`}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {/* Chart Type Icon */}
            <div className="bg-primary-100 rounded-lg p-2 flex-shrink-0">
              <ChartIcon className={`${compact ? 'h-3 w-3' : 'h-4 w-4'} text-primary-600`} />
            </div>

            {/* Title and Subtitle */}
            <div className="min-w-0 flex-1">
              <h3
                className={`font-semibold text-gray-900 ${compact ? 'text-sm' : 'text-base'} leading-tight`}
              >
                {title}
              </h3>
              {subtitle && (
                <p className={`text-gray-600 ${compact ? 'text-xs' : 'text-sm'} mt-0.5`}>
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Trend Summary */}
          {trendSummary && (
            <div className="flex items-center gap-2 flex-shrink-0">
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                  trendSummary.direction === 'up'
                    ? 'bg-green-100 text-green-700'
                    : trendSummary.direction === 'down'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-700'
                }`}
              >
                {trendSummary.direction === 'up' && <TrendingUp className="h-3 w-3" />}
                {trendSummary.direction === 'down' && <TrendingDown className="h-3 w-3" />}
                {trendSummary.direction === 'stable' && <Activity className="h-3 w-3" />}
                <span className="font-medium">
                  {trendSummary.changePercent > 0 ? '+' : ''}
                  {trendSummary.changePercent.toFixed(1)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className={compact ? 'p-2' : 'p-4'}>
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      </div>

      {/* Footer with summary stats */}
      {!compact && data.length > 0 && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 rounded-b-lg">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <Info className="h-3 w-3" />
              <span>{data.length} data points</span>
            </div>

            {typeof data[0]?.value === 'number' && (
              <div className="flex items-center gap-4">
                <span>
                  Max:{' '}
                  {formatValue(
                    Math.max(
                      ...data
                        .filter((d) => typeof d.value === 'number')
                        .map((d) => d.value as number)
                    )
                  )}
                </span>
                <span>
                  Min:{' '}
                  {formatValue(
                    Math.min(
                      ...data
                        .filter((d) => typeof d.value === 'number')
                        .map((d) => d.value as number)
                    )
                  )}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Helper component for rendering multiple metrics in a grid
interface MetricsGridProps {
  metrics: Array<{
    title: string
    subtitle?: string
    data: DataPoint[]
    chartType: ChartType
    dataType?: DataType
  }>
  columns?: 1 | 2 | 3
  compact?: boolean
  className?: string
}

export function MetricsGrid({
  metrics,
  columns = 2,
  compact = false,
  className = '',
}: MetricsGridProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  }

  return (
    <div className={`grid ${gridCols[columns]} gap-4 ${className}`}>
      {metrics.map((metric, index) => (
        <MetricsVisualization
          key={index}
          title={metric.title}
          subtitle={metric.subtitle}
          data={metric.data}
          chartType={metric.chartType}
          dataType={metric.dataType}
          compact={compact}
          height={compact ? 200 : 300}
        />
      ))}
    </div>
  )
}
