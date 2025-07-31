import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'

interface TrendDataPoint {
  period: string
  value: number
  label?: string
  target?: number
}

interface TrendChartProps {
  data: TrendDataPoint[]
  title?: string
  subtitle?: string
  height?: number
  color?: string
  showTarget?: boolean
  targetLabel?: string
  formatValue?: (value: number) => string
  showGradient?: boolean
  className?: string
}

export function TrendChart({
  data,
  title,
  subtitle,
  height = 300,
  color = '#6366f1',
  showTarget = false,
  targetLabel = 'Target',
  formatValue,
  showGradient = false,
  className = '',
}: TrendChartProps) {
  const defaultFormatter = (value: number) => {
    if (Math.abs(value) >= 1e9) {
      return `$${(value / 1e9).toFixed(1)}B`
    } else if (Math.abs(value) >= 1e6) {
      return `$${(value / 1e6).toFixed(1)}M`
    } else if (Math.abs(value) >= 1e3) {
      return `$${(value / 1e3).toFixed(1)}K`
    } else {
      return `$${value.toLocaleString()}`
    }
  }

  const valueFormatter = formatValue || defaultFormatter

  // Calculate trend direction
  const calculateTrend = () => {
    if (data.length < 2) return null
    const firstValue = data[0].value
    const lastValue = data[data.length - 1].value
    const change = ((lastValue - firstValue) / firstValue) * 100
    return {
      direction: change > 0 ? 'up' : change < 0 ? 'down' : 'flat',
      percentage: Math.abs(change),
    }
  }

  const trend = calculateTrend()

  const getTrendColor = () => {
    if (!trend) return color
    switch (trend.direction) {
      case 'up':
        return '#10b981' // success-500
      case 'down':
        return '#ef4444' // error-500
      default:
        return '#64748b' // gray-500
    }
  }

  const getTrendIcon = () => {
    if (!trend) return null
    switch (trend.direction) {
      case 'up':
        return '↗'
      case 'down':
        return '↘'
      default:
        return '→'
    }
  }

  // Find average target value for reference line
  const averageTarget =
    showTarget && data.some((d) => d.target)
      ? data.reduce((sum, d) => sum + (d.target || 0), 0) / data.filter((d) => d.target).length
      : null

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      {(title || subtitle || trend) && (
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div>
              {title && <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>}
              {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
            </div>
            {trend && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-500">Trend:</span>
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                    trend.direction === 'up'
                      ? 'bg-success-100 text-success-800'
                      : trend.direction === 'down'
                        ? 'bg-error-100 text-error-800'
                        : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  <span>{getTrendIcon()}</span>
                  <span>{trend.percentage.toFixed(1)}%</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="p-6">
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            {showGradient && (
              <defs>
                <linearGradient
                  id={`gradient-${color.replace('#', '')}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={color} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.1} />
                </linearGradient>
              </defs>
            )}

            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />

            <XAxis
              dataKey="period"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: '#6b7280' }}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickFormatter={valueFormatter}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              formatter={(value: any, name: string) => [valueFormatter(value), name]}
              labelStyle={{ color: '#374151', fontWeight: 500 }}
            />

            {showTarget && <Legend />}

            {/* Reference line for target */}
            {averageTarget && (
              <ReferenceLine
                y={averageTarget}
                stroke="#f59e0b"
                strokeDasharray="5 5"
                label={{ value: targetLabel, position: 'top' }}
              />
            )}

            {/* Main trend line */}
            <Line
              type="monotone"
              dataKey="value"
              name="Value"
              stroke={showGradient ? `url(#gradient-${color.replace('#', '')})` : getTrendColor()}
              strokeWidth={3}
              dot={{
                fill: getTrendColor(),
                strokeWidth: 2,
                r: 5,
                stroke: 'white',
              }}
              activeDot={{
                r: 7,
                fill: getTrendColor(),
                stroke: 'white',
                strokeWidth: 2,
              }}
              fill={showGradient ? `url(#gradient-${color.replace('#', '')})` : 'none'}
            />

            {/* Target line */}
            {showTarget && (
              <Line
                type="monotone"
                dataKey="target"
                name={targetLabel}
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Stats */}
      {data.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Current</div>
              <div className="text-sm font-semibold text-gray-900 mt-1">
                {valueFormatter(data[data.length - 1].value)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Average</div>
              <div className="text-sm font-semibold text-gray-900 mt-1">
                {valueFormatter(data.reduce((sum, d) => sum + d.value, 0) / data.length)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">Peak</div>
              <div className="text-sm font-semibold text-gray-900 mt-1">
                {valueFormatter(Math.max(...data.map((d) => d.value)))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
