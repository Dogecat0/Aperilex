import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Building,
  DollarSign,
  AlertTriangle,
  FileText,
  Target,
  TrendingUp,
} from 'lucide-react'
import type { AnalysisSchemaData } from '@/api/types'

interface AnalysisDetailCardProps {
  title: string
  schemaType: string
  analysisData: AnalysisSchemaData
  parentSection: string
  className?: string
  defaultExpanded?: boolean
}

export function AnalysisDetailCard({
  title,
  schemaType,
  analysisData,
  parentSection,
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
        gradient: 'bg-gradient-to-br from-teal-50 to-cyan-50',
        borderColor: 'border-teal-200',
        iconBg: 'bg-teal-100',
        iconColor: 'text-teal-700',
        accentColor: 'text-teal-600',
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
        gradient: 'bg-gradient-to-br from-blue-50 to-indigo-50',
        borderColor: 'border-blue-200',
        iconBg: 'bg-blue-100',
        iconColor: 'text-blue-700',
        accentColor: 'text-blue-600',
      }
    }

    if (normalizedType.includes('risk')) {
      return {
        icon: AlertTriangle,
        gradient: 'bg-gradient-to-br from-red-50 to-pink-50',
        borderColor: 'border-red-200',
        iconBg: 'bg-red-100',
        iconColor: 'text-red-700',
        accentColor: 'text-red-600',
      }
    }

    if (normalizedType.includes('mda') || normalizedType.includes('management')) {
      return {
        icon: TrendingUp,
        gradient: 'bg-gradient-to-br from-purple-50 to-indigo-50',
        borderColor: 'border-purple-200',
        iconBg: 'bg-purple-100',
        iconColor: 'text-purple-700',
        accentColor: 'text-purple-600',
      }
    }

    // Default
    return {
      icon: FileText,
      gradient: 'bg-gradient-to-br from-gray-50 to-slate-50',
      borderColor: 'border-gray-200',
      iconBg: 'bg-gray-100',
      iconColor: 'text-gray-700',
      accentColor: 'text-gray-600',
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
          ? 'text-sm font-semibold text-gray-900 mb-2'
          : 'text-xs font-medium text-gray-700 mb-1'

      if (typeof value === 'string') {
        if (value.length === 0) return null
        return (
          <div key={key} className={`${indent} mb-3`}>
            <div className={keyClass}>{formatKey(key)}</div>
            <p className="text-sm text-gray-700 leading-relaxed">{value}</p>
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
                <li key={index} className="flex gap-2 text-sm text-gray-700">
                  <div className="w-1 h-1 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
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
            <div className="bg-gray-50 rounded-lg p-3 space-y-2">
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
          <span className="text-sm text-gray-700 ml-2">
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
      <div key={index} className="bg-white border border-gray-100 rounded-md p-3 mt-2">
        {Object.entries(obj).map(([key, value]) => (
          <div key={key} className="mb-2">
            <span className="text-xs font-medium text-gray-600">{formatKey(key)}:</span>
            <span className="text-sm text-gray-800 ml-1">
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
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            {/* Icon */}
            <div className={`${config.iconBg} rounded-lg p-2 flex-shrink-0`}>
              <Icon className={`h-4 w-4 ${config.iconColor}`} />
            </div>

            {/* Title and Meta */}
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-gray-900 text-sm mb-1 leading-tight">{title}</h3>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className="inline-flex items-center gap-1">
                  <Target className="h-3 w-3" />
                  {schemaType}
                </span>
                <span>"</span>
                <span className="inline-flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {parentSection}
                </span>
              </div>
            </div>
          </div>

          {/* Expand Toggle */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex-shrink-0 p-1 hover:bg-gray-100 rounded-md transition-colors"
            title={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-500" />
            )}
          </button>
        </div>

        {/* Preview when collapsed */}
        {!isExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-sm text-gray-600 line-clamp-2">{getContentPreview()}</p>
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
