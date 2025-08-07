import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Download,
  Share,
  Clock,
  Target,
  AlertTriangle,
  DollarSign,
  Building,
  Shield,
  FileText,
  BarChart3,
} from 'lucide-react'
import { ConfidenceIndicator } from './ConfidenceIndicator'

type AnalysisType = 'financial' | 'risk' | 'business' | 'default'
type SizeVariant = 'sm' | 'md' | 'lg'

interface SectionMetadata {
  confidence?: number | null
  processingTimeMs?: number | null
  subSectionCount?: number
  totalItems?: number
}

interface QuickAction {
  icon: React.ComponentType<{ className?: string }>
  label: string
  onClick: () => void
  disabled?: boolean
}

interface EnhancedSectionHeaderProps {
  title: string
  subtitle?: string
  analysisType?: AnalysisType
  size?: SizeVariant
  isExpanded?: boolean
  onToggle?: () => void
  metadata?: SectionMetadata
  quickActions?: {
    showExport?: boolean
    showShare?: boolean
    onExport?: () => void
    onShare?: () => void
    customActions?: QuickAction[]
  }
  className?: string
}

export function EnhancedSectionHeader({
  title,
  subtitle,
  analysisType = 'default',
  size = 'md',
  isExpanded,
  onToggle,
  metadata,
  quickActions,
  className = '',
}: EnhancedSectionHeaderProps) {
  const [isHovered, setIsHovered] = useState(false)

  // Get gradient and color schemes based on analysis type
  const getThemeConfig = (type: AnalysisType) => {
    switch (type) {
      case 'financial':
        return {
          gradient: 'bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600',
          lightGradient: 'bg-gradient-to-r from-blue-50 to-indigo-50',
          iconBg: 'bg-blue-100',
          iconColor: 'text-blue-700',
          textColor: 'text-white',
          hoverGradient: 'bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700',
          borderColor: 'border-blue-200',
          icon: DollarSign,
        }
      case 'risk':
        return {
          gradient: 'bg-gradient-to-r from-red-500 via-red-600 to-pink-600',
          lightGradient: 'bg-gradient-to-r from-red-50 to-pink-50',
          iconBg: 'bg-red-100',
          iconColor: 'text-red-700',
          textColor: 'text-white',
          hoverGradient: 'bg-gradient-to-r from-red-600 via-red-700 to-pink-700',
          borderColor: 'border-red-200',
          icon: AlertTriangle,
        }
      case 'business':
        return {
          gradient: 'bg-gradient-to-r from-teal-500 via-teal-600 to-cyan-600',
          lightGradient: 'bg-gradient-to-r from-teal-50 to-cyan-50',
          iconBg: 'bg-teal-100',
          iconColor: 'text-teal-700',
          textColor: 'text-white',
          hoverGradient: 'bg-gradient-to-r from-teal-600 via-teal-700 to-cyan-700',
          borderColor: 'border-teal-200',
          icon: Building,
        }
      default:
        return {
          gradient: 'bg-gradient-to-r from-gray-500 via-gray-600 to-slate-600',
          lightGradient: 'bg-gradient-to-r from-gray-50 to-slate-50',
          iconBg: 'bg-gray-100',
          iconColor: 'text-gray-700',
          textColor: 'text-white',
          hoverGradient: 'bg-gradient-to-r from-gray-600 via-gray-700 to-slate-700',
          borderColor: 'border-gray-200',
          icon: FileText,
        }
    }
  }

  // Get size-specific classes
  const getSizeConfig = (size: SizeVariant) => {
    switch (size) {
      case 'sm':
        return {
          container: 'p-3',
          iconContainer: 'w-8 h-8 p-1.5',
          icon: 'h-4 w-4',
          title: 'text-sm font-semibold',
          subtitle: 'text-xs',
          metadata: 'text-xs',
          actionButton: 'w-7 h-7 p-1',
          actionIcon: 'h-3 w-3',
        }
      case 'lg':
        return {
          container: 'p-6',
          iconContainer: 'w-12 h-12 p-2.5',
          icon: 'h-6 w-6',
          title: 'text-xl font-bold',
          subtitle: 'text-base',
          metadata: 'text-sm',
          actionButton: 'w-10 h-10 p-2',
          actionIcon: 'h-5 w-5',
        }
      default: // md
        return {
          container: 'p-4',
          iconContainer: 'w-10 h-10 p-2',
          icon: 'h-5 w-5',
          title: 'text-lg font-semibold',
          subtitle: 'text-sm',
          metadata: 'text-sm',
          actionButton: 'w-8 h-8 p-1.5',
          actionIcon: 'h-4 w-4',
        }
    }
  }

  const theme = getThemeConfig(analysisType)
  const sizeConfig = getSizeConfig(size)
  const ThemeIcon = theme.icon

  // Format processing time
  const formatProcessingTime = (timeMs: number) => {
    if (timeMs < 1000) return `${timeMs}ms`
    return `${Math.round(timeMs / 1000)}s`
  }

  // Create default quick actions
  const defaultQuickActions: QuickAction[] = []
  
  if (quickActions?.showExport && quickActions?.onExport) {
    defaultQuickActions.push({
      icon: Download,
      label: 'Export',
      onClick: quickActions.onExport,
    })
  }
  
  if (quickActions?.showShare && quickActions?.onShare) {
    defaultQuickActions.push({
      icon: Share,
      label: 'Share',
      onClick: quickActions.onShare,
    })
  }

  const allQuickActions = [
    ...defaultQuickActions,
    ...(quickActions?.customActions || [])
  ]

  return (
    <div
      className={`rounded-lg border shadow-sm transition-all duration-200 ${
        isHovered ? 'shadow-md' : ''
      } ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Main Header */}
      <div
        className={`${
          isHovered ? theme.hoverGradient : theme.gradient
        } ${sizeConfig.container} transition-all duration-200`}
      >
        <div className="flex items-center justify-between">
          {/* Left Section - Icon and Title */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {/* Icon Badge */}
            <div
              className={`${sizeConfig.iconContainer} ${theme.iconBg} rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm`}
            >
              <ThemeIcon className={`${sizeConfig.icon} ${theme.iconColor}`} />
            </div>

            {/* Title and Subtitle */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className={`${sizeConfig.title} ${theme.textColor} truncate`}>
                  {title}
                </h3>
                {metadata?.confidence !== undefined && metadata?.confidence !== null && (
                  <ConfidenceIndicator
                    score={metadata.confidence}
                    size={size === 'lg' ? 'md' : 'sm'}
                  />
                )}
              </div>
              {subtitle && (
                <p className={`${sizeConfig.subtitle} ${theme.textColor} opacity-90 mt-0.5 truncate`}>
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Right Section - Metadata and Actions */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Metadata */}
            {metadata && (
              <div className={`flex items-center gap-3 ${sizeConfig.metadata} ${theme.textColor} opacity-90`}>
                {metadata.processingTimeMs && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatProcessingTime(metadata.processingTimeMs)}</span>
                  </div>
                )}
                {metadata.subSectionCount && metadata.subSectionCount > 0 && (
                  <div className="flex items-center gap-1">
                    <BarChart3 className="h-3 w-3" />
                    <span>{metadata.subSectionCount} sections</span>
                  </div>
                )}
                {metadata.totalItems && (
                  <div className="flex items-center gap-1">
                    <Target className="h-3 w-3" />
                    <span>{metadata.totalItems} items</span>
                  </div>
                )}
              </div>
            )}

            {/* Quick Actions */}
            {allQuickActions.length > 0 && (
              <div className="flex items-center gap-1">
                {allQuickActions.map((action, index) => (
                  <button
                    key={index}
                    onClick={action.onClick}
                    disabled={action.disabled}
                    className={`${sizeConfig.actionButton} ${theme.textColor} hover:bg-white hover:bg-opacity-20 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center`}
                    title={action.label}
                  >
                    <action.icon className={sizeConfig.actionIcon} />
                  </button>
                ))}
              </div>
            )}

            {/* Expand/Collapse Toggle */}
            {onToggle && (
              <button
                onClick={onToggle}
                className={`${sizeConfig.actionButton} ${theme.textColor} hover:bg-white hover:bg-opacity-20 rounded-md transition-colors flex items-center justify-center ml-1`}
                title={isExpanded ? 'Collapse section' : 'Expand section'}
              >
                {isExpanded ? (
                  <ChevronDown className={sizeConfig.actionIcon} />
                ) : (
                  <ChevronRight className={sizeConfig.actionIcon} />
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Optional Light Background Bar for Additional Info */}
      {(metadata?.subSectionCount || metadata?.totalItems) && (
        <div className={`${theme.lightGradient} border-t ${theme.borderColor} px-4 py-2`}>
          <div className="flex items-center justify-between text-xs text-gray-600">
            <div className="flex items-center gap-4">
              {metadata.subSectionCount && (
                <span>{metadata.subSectionCount} sub-sections analyzed</span>
              )}
              {metadata.totalItems && (
                <span>{metadata.totalItems} data points extracted</span>
              )}
            </div>
            {metadata.confidence !== undefined && metadata.confidence !== null && (
              <div className="flex items-center gap-1">
                <Shield className="h-3 w-3" />
                <span>Analysis confidence: {Math.round(metadata.confidence * 100)}%</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Export helper function to determine analysis type from section name
export function getAnalysisType(sectionName: string): AnalysisType {
  const name = sectionName.toLowerCase()
  if (name.includes('financial') || name.includes('balance') || name.includes('income') || name.includes('cash')) {
    return 'financial'
  }
  if (name.includes('risk') || name.includes('factor')) {
    return 'risk'
  }
  if (name.includes('business') || name.includes('operation') || name.includes('market')) {
    return 'business'
  }
  return 'default'
}

// Export helper function to extract metadata from section data
export function extractSectionMetadata(section: any): SectionMetadata {
  return {
    confidence: section.confidence_score || section.overall_confidence || null,
    processingTimeMs: section.processing_time_ms || null,
    subSectionCount: section.sub_section_count || section.sub_sections?.length || 0,
    totalItems: section.total_items || null,
  }
}