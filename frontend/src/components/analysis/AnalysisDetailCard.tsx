import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Building,
  DollarSign,
  AlertTriangle,
  FileText,
  TrendingUp,
} from 'lucide-react'
import type { AnalysisSchemaData } from '@/api/types'

interface AnalysisDetailCardProps {
  title: string
  schemaType: string
  analysisData: AnalysisSchemaData
  className?: string
  defaultExpanded?: boolean
}

export function AnalysisDetailCard({
  title,
  schemaType,
  analysisData,
  className = '',
  defaultExpanded = false,
}: AnalysisDetailCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  // Get icon and theme based on schema type
  const getSchemaConfig = (type: string) => {
    const normalizedType = type.toLowerCase()

    if (normalizedType.includes('business')) {
      return {
        icon: Building,
        gradient: 'bg-primary/5 hover:bg-primary/10',
        borderColor: 'border-primary/20',
        iconBg: 'bg-primary/10',
        iconColor: 'text-primary',
        accentColor: 'text-primary',
      }
    }

    if (
      normalizedType.includes('financial') ||
      normalizedType.includes('balance') ||
      normalizedType.includes('income') ||
      normalizedType.includes('cash')
    ) {
      return {
        icon: DollarSign,
        gradient: 'bg-green-500/5 hover:bg-green-500/10',
        borderColor: 'border-green-500/20',
        iconBg: 'bg-green-500/10',
        iconColor: 'text-green-600 dark:text-green-400',
        accentColor: 'text-green-600 dark:text-green-400',
      }
    }

    if (normalizedType.includes('risk')) {
      return {
        icon: AlertTriangle,
        gradient: 'bg-destructive/5 hover:bg-destructive/10',
        borderColor: 'border-destructive/20',
        iconBg: 'bg-destructive/10',
        iconColor: 'text-destructive',
        accentColor: 'text-destructive',
      }
    }

    if (normalizedType.includes('mda') || normalizedType.includes('management')) {
      return {
        icon: TrendingUp,
        gradient: 'bg-yellow-500/5 hover:bg-yellow-500/10',
        borderColor: 'border-yellow-500/20',
        iconBg: 'bg-yellow-500/10',
        iconColor: 'text-yellow-600 dark:text-yellow-400',
        accentColor: 'text-yellow-600 dark:text-yellow-400',
      }
    }

    // Default
    return {
      icon: FileText,
      gradient: 'bg-muted/50 hover:bg-muted/70',
      borderColor: 'border-border',
      iconBg: 'bg-muted',
      iconColor: 'text-foreground/80',
      accentColor: 'text-muted-foreground',
    }
  }

  const config = getSchemaConfig(schemaType)
  const Icon = config.icon

  // Helper function to render different types of content
  const renderContent = () => {
    if (!analysisData) return null

    const renderSection = (key: string, value: any, level: number = 0) => {
      if (value === null || value === undefined) return null

      const indent = level > 0 ? `ml-${level * 4}` : ''
      const keyClass =
        level === 0
          ? 'text-sm font-semibold text-foreground mb-2'
          : 'text-xs font-medium text-foreground/80 mb-1'

      if (typeof value === 'string') {
        if (value.length === 0) return null
        return (
          <div key={key} className={`${indent} mb-3`}>
            <div className={keyClass}>{formatKey(key)}</div>
            <p className="text-sm text-foreground/80 leading-relaxed">{value}</p>
          </div>
        )
      }

      if (Array.isArray(value)) {
        if (value.length === 0) return null
        return (
          <div key={key} className={`${indent} mb-3`}>
            <div className={keyClass}>
              {formatKey(key)} ({value.length})
            </div>
            <ul className="space-y-2">
              {value.map((item, index) => (
                <li key={index} className="flex gap-2 text-sm text-foreground/80">
                  <div className="w-1 h-1 bg-primary rounded-full mt-2 flex-shrink-0"></div>
                  <div className="flex-1">
                    {typeof item === 'object' ? renderObjectAsCard(item, index) : item}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )
      }

      if (typeof value === 'object') {
        return (
          <div key={key} className={`${indent} mb-4`}>
            <div className={keyClass}>{formatKey(key)}</div>
            <div className="bg-muted/50 rounded-lg p-3 space-y-2">
              {Object.entries(value).map(([subKey, subValue]) =>
                renderSection(subKey, subValue, level + 1)
              )}
            </div>
          </div>
        )
      }

      // Number or boolean
      return (
        <div key={key} className={`${indent} mb-2`}>
          <span className={keyClass}>{formatKey(key)}:</span>
          <span className="text-sm text-foreground/80 ml-2">
            {typeof value === 'number' ? value.toLocaleString() : String(value)}
          </span>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {Object.entries(analysisData).map(([key, value]) => renderSection(key, value))}
      </div>
    )
  }

  const renderObjectAsCard = (obj: any, index: number) => {
    return (
      <div key={index} className="bg-card border border-border/50 rounded-md p-3 mt-2">
        {Object.entries(obj).map(([key, value]) => (
          <div key={key} className="mb-2">
            <span className="text-xs font-medium text-muted-foreground">{formatKey(key)}:</span>
            <span className="text-sm text-foreground ml-1">
              {Array.isArray(value) ? value.join(', ') : String(value)}
            </span>
          </div>
        ))}
      </div>
    )
  }

  const formatKey = (key: string) => {
    return key
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const getContentPreview = () => {
    if (!analysisData || typeof analysisData !== 'object') return ''

    // Try to find a summary or description field
    const data = analysisData as any
    if (data.executive_summary) return data.executive_summary
    if (data.section_summary) return data.section_summary
    if (data.description) return data.description
    if (data.operational_overview?.description) return data.operational_overview.description

    // Fallback to first string field
    for (const [_key, value] of Object.entries(data)) {
      if (typeof value === 'string' && value.length > 50) {
        return value
      }
    }

    return 'Detailed analysis data available'
  }

  return (
    <div
      className={`rounded-lg border ${config.borderColor} ${config.gradient} shadow-sm hover:shadow-md transition-all duration-200 ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            {/* Icon */}
            <div className={`${config.iconBg} rounded-lg p-2 flex-shrink-0`}>
              <Icon className={`h-4 w-4 ${config.iconColor}`} />
            </div>

            {/* Title and Meta */}
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-foreground text-sm mb-1 leading-tight">{title}</h3>
            </div>
          </div>

          {/* Expand Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex-shrink-0 p-1 hover:bg-muted/50 rounded-md transition-colors"
            title={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground/70" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground/70" />
            )}
          </button>
        </div>

        {/* Preview when collapsed */}
        {!isExpanded && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <p className="text-sm text-muted-foreground line-clamp-2">{getContentPreview()}</p>
          </div>
        )}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4">
          <div className="prose prose-sm max-w-none">{renderContent()}</div>
        </div>
      )}
    </div>
  )
}
