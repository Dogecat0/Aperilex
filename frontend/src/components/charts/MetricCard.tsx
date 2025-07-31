import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string | number
  previousValue?: string | number
  change?: number
  changeLabel?: string
  icon?: LucideIcon
  iconColor?: string
  size?: 'sm' | 'md' | 'lg'
  format?: 'number' | 'currency' | 'percentage' | 'text'
  className?: string
}

export function MetricCard({
  label,
  value,
  previousValue,
  change,
  changeLabel,
  icon: Icon,
  iconColor = 'text-primary-600 bg-primary-50',
  size = 'md',
  format = 'text',
  className = '',
}: MetricCardProps) {
  const formatValue = (val: string | number, fmt: string) => {
    if (typeof val === 'string') return val

    switch (fmt) {
      case 'currency':
        if (Math.abs(val) >= 1e9) {
          return `$${(val / 1e9).toFixed(1)}B`
        } else if (Math.abs(val) >= 1e6) {
          return `$${(val / 1e6).toFixed(1)}M`
        } else if (Math.abs(val) >= 1e3) {
          return `$${(val / 1e3).toFixed(1)}K`
        } else {
          return `$${val.toLocaleString()}`
        }
      case 'percentage':
        return `${val.toFixed(1)}%`
      case 'number':
        return val.toLocaleString()
      default:
        return val.toString()
    }
  }

  const getChangeIcon = (changeValue?: number) => {
    if (!changeValue) return null
    if (changeValue > 0) return TrendingUp
    if (changeValue < 0) return TrendingDown
    return Minus
  }

  const getChangeColor = (changeValue?: number) => {
    if (!changeValue) return 'text-gray-500'
    if (changeValue > 0) return 'text-success-600'
    if (changeValue < 0) return 'text-error-600'
    return 'text-gray-500'
  }

  const sizeClasses = {
    sm: {
      container: 'p-3',
      icon: 'h-6 w-6 p-1',
      value: 'text-lg',
      label: 'text-xs',
      change: 'text-xs',
    },
    md: {
      container: 'p-4',
      icon: 'h-8 w-8 p-1.5',
      value: 'text-2xl',
      label: 'text-sm',
      change: 'text-sm',
    },
    lg: {
      container: 'p-6',
      icon: 'h-10 w-10 p-2',
      value: 'text-3xl',
      label: 'text-base',
      change: 'text-base',
    },
  }

  const classes = sizeClasses[size]
  const ChangeIcon = getChangeIcon(change)
  const formattedValue = formatValue(value, format)
  const formattedPreviousValue = previousValue ? formatValue(previousValue, format) : null

  return (
    <div
      className={`bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow ${classes.container} ${className}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {Icon && (
              <div
                className={`${classes.icon} ${iconColor} rounded-lg flex items-center justify-center flex-shrink-0`}
              >
                <Icon className="h-full w-full" />
              </div>
            )}
            <p className={`${classes.label} font-medium text-gray-700 truncate`}>{label}</p>
          </div>

          <div className="space-y-1">
            <p className={`${classes.value} font-bold text-gray-900`}>{formattedValue}</p>

            {/* Previous value */}
            {formattedPreviousValue && (
              <p className={`${classes.change} text-gray-500`}>
                Previous: {formattedPreviousValue}
              </p>
            )}

            {/* Change indicator */}
            {(change !== undefined || changeLabel) && (
              <div className={`flex items-center gap-1 ${classes.change}`}>
                {ChangeIcon && <ChangeIcon className={`h-3 w-3 ${getChangeColor(change)}`} />}
                <span className={getChangeColor(change)}>
                  {changeLabel ||
                    (change !== undefined
                      ? `${change > 0 ? '+' : ''}${change.toFixed(1)}%`
                      : 'No change')}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
