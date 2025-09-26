import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'

interface ComparisonDataPoint {
  name: string
  value: number
  previousValue?: number
  target?: number
  category?: string
  color?: string
}

interface ComparisonChartProps {
  data: ComparisonDataPoint[]
  title?: string
  subtitle?: string
  height?: number
  orientation?: 'vertical' | 'horizontal'
  showComparison?: boolean
  showTarget?: boolean
  formatValue?: (value: number) => string
  colorScheme?: 'default' | 'financial' | 'categorical'
  className?: string
}

export function ComparisonChart({
  data,
  title,
  subtitle,
  height = 300,
  orientation = 'vertical',
  showComparison = false,
  showTarget = false,
  formatValue,
  colorScheme = 'default',
  className = '',
}: ComparisonChartProps) {
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

  const getColorScheme = () => {
    switch (colorScheme) {
      case 'financial':
        return {
          primary: '#10b981', // success-500 for profit/positive
          secondary: '#ef4444', // error-500 for loss/negative
          neutral: '#64748b', // gray-500 for neutral
        }
      case 'categorical':
        return [
          '#6366f1', // primary
          '#14b8a6', // teal
          '#f59e0b', // amber
          '#ef4444', // red
          '#8b5cf6', // violet
          '#06b6d4', // cyan
          '#84cc16', // lime
          '#f97316', // orange
        ]
      default:
        return {
          primary: '#6366f1',
          secondary: '#94a3b8',
          target: '#f59e0b',
        }
    }
  }

  const colors = getColorScheme()

  const getBarColor = (dataPoint: ComparisonDataPoint, index: number) => {
    if (dataPoint.color) return dataPoint.color

    if (colorScheme === 'financial') {
      const colorObj = colors as { primary: string; secondary: string; neutral: string }
      if (dataPoint.value > 0) return colorObj.primary
      if (dataPoint.value < 0) return colorObj.secondary
      return colorObj.neutral
    }

    if (colorScheme === 'categorical' && Array.isArray(colors)) {
      return colors[index % colors.length]
    }

    const colorObj = colors as { primary: string; secondary?: string; target?: string }
    return colorObj.primary
  }

  // Calculate summary statistics
  const totalValue = data.reduce((sum, d) => sum + d.value, 0)
  const averageValue = totalValue / data.length
  const maxValue = Math.max(...data.map((d) => d.value))
  const minValue = Math.min(...data.map((d) => d.value))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-gray-600">Current:</span>
              <span className="text-sm font-semibold text-gray-900">
                {valueFormatter(data.value)}
              </span>
            </div>
            {showComparison && data.previousValue !== undefined && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-gray-600">Previous:</span>
                <span className="text-sm text-gray-700">{valueFormatter(data.previousValue)}</span>
              </div>
            )}
            {showTarget && data.target !== undefined && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-gray-600">Target:</span>
                <span className="text-sm text-warning-700">{valueFormatter(data.target)}</span>
              </div>
            )}
            {showComparison && data.previousValue !== undefined && (
              <div className="pt-2 border-t border-gray-100">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-xs text-gray-500">Change:</span>
                  <span
                    className={`text-xs font-medium ${
                      data.value > data.previousValue
                        ? 'text-success-600'
                        : data.value < data.previousValue
                          ? 'text-error-600'
                          : 'text-gray-600'
                    }`}
                  >
                    {data.value > data.previousValue ? '+' : ''}
                    {(((data.value - data.previousValue) / data.previousValue) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      {(title || subtitle) && (
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div>
              {title && <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>}
              {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">Total</div>
              <div className="text-lg font-semibold text-gray-900">
                {valueFormatter(totalValue)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="p-6">
        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={data}
            layout={orientation === 'horizontal' ? 'horizontal' : 'vertical'}
            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />

            {orientation === 'vertical' ? (
              <>
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  angle={data.length > 6 ? -45 : 0}
                  textAnchor={data.length > 6 ? 'end' : 'middle'}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  tickFormatter={valueFormatter}
                />
              </>
            ) : (
              <>
                <XAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  tickFormatter={valueFormatter}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  width={80}
                />
              </>
            )}

            <Tooltip content={<CustomTooltip />} />

            {(showComparison || showTarget) && <Legend />}

            {/* Main bars */}
            <Bar
              dataKey="value"
              name="Current"
              radius={orientation === 'vertical' ? [4, 4, 0, 0] : [0, 4, 4, 0]}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry, index)} />
              ))}
            </Bar>

            {/* Previous value comparison bars */}
            {showComparison && (
              <Bar
                dataKey="previousValue"
                name="Previous"
                radius={orientation === 'vertical' ? [4, 4, 0, 0] : [0, 4, 4, 0]}
                opacity={0.6}
              >
                {data.map((entry, index) => (
                  <Cell key={`prev-cell-${index}`} fill={getBarColor(entry, index)} />
                ))}
              </Bar>
            )}

            {/* Target bars */}
            {showTarget && (
              <Bar
                dataKey="target"
                name="Target"
                radius={orientation === 'vertical' ? [4, 4, 0, 0] : [0, 4, 4, 0]}
                fill={Array.isArray(colors) ? '#f59e0b' : colors.target}
                opacity={0.7}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Statistics */}
      <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Average</div>
            <div className="text-sm font-semibold text-gray-900 mt-1">
              {valueFormatter(averageValue)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Highest</div>
            <div className="text-sm font-semibold text-success-600 mt-1">
              {valueFormatter(maxValue)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Lowest</div>
            <div className="text-sm font-semibold text-error-600 mt-1">
              {valueFormatter(minValue)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Range</div>
            <div className="text-sm font-semibold text-gray-900 mt-1">
              {valueFormatter(maxValue - minValue)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
