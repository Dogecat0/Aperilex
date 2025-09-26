import { Shield, ShieldCheck, ShieldX, ShieldAlert } from 'lucide-react'

interface ConfidenceIndicatorProps {
  score?: number | null
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function ConfidenceIndicator({
  score,
  size = 'md',
  showLabel = false,
  className = '',
}: ConfidenceIndicatorProps) {
  if (score === null || score === undefined) {
    return (
      <div className={`inline-flex items-center gap-1 text-gray-400 ${className}`}>
        <Shield
          className={`${size === 'sm' ? 'h-3 w-3' : size === 'lg' ? 'h-5 w-5' : 'h-4 w-4'}`}
        />
        {showLabel && <span className="text-xs">N/A</span>}
      </div>
    )
  }

  const getConfidenceConfig = (score: number) => {
    if (score >= 0.8) {
      return {
        label: 'High Confidence',
        color: 'text-success-600',
        bgColor: 'bg-success-100',
        borderColor: 'border-success-200',
        icon: ShieldCheck,
      }
    } else if (score >= 0.6) {
      return {
        label: 'Good Confidence',
        color: 'text-success-600',
        bgColor: 'bg-success-50',
        borderColor: 'border-success-200',
        icon: Shield,
      }
    } else if (score >= 0.4) {
      return {
        label: 'Moderate Confidence',
        color: 'text-warning-600',
        bgColor: 'bg-warning-50',
        borderColor: 'border-warning-200',
        icon: ShieldAlert,
      }
    } else {
      return {
        label: 'Low Confidence',
        color: 'text-error-600',
        bgColor: 'bg-error-50',
        borderColor: 'border-error-200',
        icon: ShieldX,
      }
    }
  }

  const config = getConfidenceConfig(score)
  const Icon = config.icon
  const percentage = Math.round(score * 100)

  const sizeClasses = {
    sm: {
      icon: 'h-3 w-3',
      text: 'text-xs',
      container: 'px-2 py-0.5',
    },
    md: {
      icon: 'h-4 w-4',
      text: 'text-sm',
      container: 'px-2.5 py-1',
    },
    lg: {
      icon: 'h-5 w-5',
      text: 'text-base',
      container: 'px-3 py-1.5',
    },
  }

  const classes = sizeClasses[size]

  if (showLabel) {
    return (
      <div
        className={`inline-flex items-center gap-2 ${config.bgColor} ${config.borderColor} ${classes.container} rounded-full border font-medium ${className}`}
      >
        <Icon className={`${classes.icon} ${config.color}`} />
        <span className={`${config.color} ${classes.text}`}>{percentage}%</span>
        <span className={`text-gray-600 ${classes.text}`}>({config.label.split(' ')[0]})</span>
      </div>
    )
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 ${config.bgColor} ${config.borderColor} ${classes.container} rounded-full border ${className}`}
    >
      <Icon className={`${classes.icon} ${config.color}`} />
      <span className={`${config.color} ${classes.text} font-medium`}>{percentage}%</span>
    </div>
  )
}
