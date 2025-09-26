import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  BarChart,
  AreaChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

interface FinancialChartProps {
  data: any[]
  type?: 'line' | 'bar' | 'area' | 'composed'
  xKey: string
  yKeys: { key: string; label: string; color?: string; type?: 'line' | 'bar' }[]
  title?: string
  height?: number
  showGrid?: boolean
  showLegend?: boolean
  showTooltip?: boolean
  formatValue?: (value: any) => string
  className?: string
}

export function FinancialChart({
  data,
  type = 'line',
  xKey,
  yKeys,
  title,
  height = 300,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  formatValue,
  className = '',
}: FinancialChartProps) {
  const colors = [
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

  const getColor = (index: number, customColor?: string) => {
    return customColor || colors[index % colors.length]
  }

  const formatTooltipValue = (value: any, name: string) => {
    if (formatValue) {
      return [formatValue(value), name]
    }

    // Auto-format common financial values
    if (typeof value === 'number') {
      if (Math.abs(value) >= 1e9) {
        return [`$${(value / 1e9).toFixed(1)}B`, name]
      } else if (Math.abs(value) >= 1e6) {
        return [`$${(value / 1e6).toFixed(1)}M`, name]
      } else if (Math.abs(value) >= 1e3) {
        return [`$${(value / 1e3).toFixed(1)}K`, name]
      } else {
        return [`$${value.toLocaleString()}`, name]
      }
    }

    return [value, name]
  }

  const renderChart = () => {
    const commonProps = {
      data,
      margin: { top: 20, right: 30, left: 20, bottom: 5 },
    }

    const xAxisProps = {
      dataKey: xKey,
      axisLine: false,
      tickLine: false,
      tick: { fontSize: 12, fill: '#6b7280' },
    }

    const yAxisProps = {
      axisLine: false,
      tickLine: false,
      tick: { fontSize: 12, fill: '#6b7280' },
      tickFormatter:
        formatValue ||
        ((value: any) => {
          if (typeof value === 'number') {
            if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
            if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
            if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(1)}K`
            return `$${value.toLocaleString()}`
          }
          return value
        }),
    }

    switch (type) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={formatTooltipValue}
              />
            )}
            {showLegend && <Legend />}
            {yKeys.map((yKey, index) => (
              <Line
                key={yKey.key}
                type="monotone"
                dataKey={yKey.key}
                name={yKey.label}
                stroke={getColor(index, yKey.color)}
                strokeWidth={2}
                dot={{ fill: getColor(index, yKey.color), strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        )

      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={formatTooltipValue}
              />
            )}
            {showLegend && <Legend />}
            {yKeys.map((yKey, index) => (
              <Bar
                key={yKey.key}
                dataKey={yKey.key}
                name={yKey.label}
                fill={getColor(index, yKey.color)}
                radius={[2, 2, 0, 0]}
              />
            ))}
          </BarChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={formatTooltipValue}
              />
            )}
            {showLegend && <Legend />}
            {yKeys.map((yKey, index) => (
              <Area
                key={yKey.key}
                type="monotone"
                dataKey={yKey.key}
                name={yKey.label}
                stroke={getColor(index, yKey.color)}
                fill={getColor(index, yKey.color)}
                fillOpacity={0.6}
              />
            ))}
          </AreaChart>
        )

      case 'composed':
        return (
          <ComposedChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />}
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={formatTooltipValue}
              />
            )}
            {showLegend && <Legend />}
            {yKeys.map((yKey, index) => {
              if (yKey.type === 'bar') {
                return (
                  <Bar
                    key={yKey.key}
                    dataKey={yKey.key}
                    name={yKey.label}
                    fill={getColor(index, yKey.color)}
                    radius={[2, 2, 0, 0]}
                  />
                )
              } else {
                return (
                  <Line
                    key={yKey.key}
                    type="monotone"
                    dataKey={yKey.key}
                    name={yKey.label}
                    stroke={getColor(index, yKey.color)}
                    strokeWidth={2}
                    dot={{ fill: getColor(index, yKey.color), strokeWidth: 2, r: 4 }}
                  />
                )
              }
            })}
          </ComposedChart>
        )

      default:
        return <div>Unsupported chart type</div>
    }
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
      )}
      <div className="p-6">
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
