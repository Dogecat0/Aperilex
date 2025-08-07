import { useState } from 'react'
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Info,
  Clock,
  Shield,
  Target,
  AlertCircle,
  TrendingDown,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { RiskFactor, RiskSeverity, RiskCategory } from '@/api/types'

interface RiskFactorCardProps {
  risk: RiskFactor | string
  index?: number
  onViewDetails?: () => void
  onAddToWatchlist?: () => void
  className?: string
}

interface RiskActionButtonsProps {
  onViewDetails?: () => void
  onAddToWatchlist?: () => void
}

export function RiskFactorCard({
  risk,
  index = 0,
  onViewDetails,
  onAddToWatchlist,
  className = '',
}: RiskFactorCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Handle both string and object risk formats
  const isObjectRisk = typeof risk === 'object' && risk !== null
  const riskData = isObjectRisk ? risk : null
  const riskText = isObjectRisk ? risk.description : risk

  // Risk severity styling
  const getSeverityConfig = (severity: RiskSeverity) => {
    const configs = {
      Critical: {
        badgeClass: 'bg-red-100 text-red-800 border-red-200',
        borderClass: 'border-l-red-500 bg-red-50',
        iconColor: 'text-red-600',
        icon: AlertCircle,
      },
      High: {
        badgeClass: 'bg-orange-100 text-orange-800 border-orange-200',
        borderClass: 'border-l-orange-500 bg-orange-50',
        iconColor: 'text-orange-600',
        icon: TrendingDown,
      },
      Medium: {
        badgeClass: 'bg-yellow-100 text-yellow-800 border-yellow-200',
        borderClass: 'border-l-yellow-500 bg-yellow-50',
        iconColor: 'text-yellow-600',
        icon: AlertTriangle,
      },
      Low: {
        badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
        borderClass: 'border-l-blue-500 bg-blue-50',
        iconColor: 'text-blue-600',
        icon: Info,
      },
    }
    return configs[severity] || configs.Medium
  }

  // Risk category icon mapping
  const getCategoryIcon = (category: RiskCategory) => {
    const categoryIcons = {
      Operational: Target,
      Financial: TrendingDown,
      Market: AlertTriangle,
      Regulatory: Shield,
      Technological: Zap,
      Strategic: Target,
      Compliance: Shield,
      Reputational: AlertCircle,
      Environmental: Info,
      Cybersecurity: Zap,
    }
    return categoryIcons[category] || AlertTriangle
  }

  const severity = riskData?.severity || 'Medium'
  const category = riskData?.category || 'Operational'
  const severityConfig = getSeverityConfig(severity)
  const CategoryIcon = getCategoryIcon(category)
  const SeverityIcon = severityConfig.icon

  return (
    <div
      className={`
        border-l-4 rounded-lg border shadow-sm transition-all duration-200 hover:shadow-md
        ${severityConfig.borderClass}
        ${className}
      `}
    >
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* Risk Icon and Title */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <SeverityIcon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${severityConfig.iconColor}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-semibold text-gray-900 text-sm leading-tight">
                  {riskData?.risk_name || `Risk Factor ${index + 1}`}
                </h3>
                {/* Expand/Collapse Button */}
                {(riskData?.mitigation_measures || 
                  riskData?.timeline || 
                  riskData?.probability ||
                  riskText.length > 200) && (
                  <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex-shrink-0 p-1 hover:bg-gray-100 rounded text-gray-500 hover:text-gray-700"
                    aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                )}
              </div>

              {/* Badges */}
              <div className="flex items-center gap-2 mb-3">
                {/* Severity Badge */}
                <span
                  className={`
                    inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border
                    ${severityConfig.badgeClass}
                  `}
                >
                  <SeverityIcon className="h-3 w-3" />
                  {severity}
                </span>

                {/* Category Badge */}
                {riskData?.category && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-full border border-gray-200">
                    <CategoryIcon className="h-3 w-3" />
                    {category}
                  </span>
                )}

                {/* Probability Badge */}
                {riskData?.probability && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded-full border border-purple-200">
                    <Info className="h-3 w-3" />
                    {riskData.probability}
                  </span>
                )}
              </div>

              {/* Risk Description */}
              <div className="text-sm text-gray-700 leading-relaxed">
                {riskText.length > 200 && !isExpanded ? (
                  <div>
                    <span>{riskText.substring(0, 200)}...</span>
                    <button
                      onClick={() => setIsExpanded(true)}
                      className="ml-2 text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Read more
                    </button>
                  </div>
                ) : (
                  riskText
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && riskData && (
          <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
            {/* Potential Impact */}
            {riskData.potential_impact && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Target className="h-4 w-4 text-gray-600" />
                  <h4 className="text-sm font-medium text-gray-900">Potential Impact</h4>
                </div>
                <p className="text-sm text-gray-700 pl-6 leading-relaxed">
                  {riskData.potential_impact}
                </p>
              </div>
            )}

            {/* Timeline */}
            {riskData.timeline && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-gray-600" />
                  <h4 className="text-sm font-medium text-gray-900">Timeline</h4>
                </div>
                <p className="text-sm text-gray-700 pl-6">
                  {riskData.timeline}
                </p>
              </div>
            )}

            {/* Mitigation Measures */}
            {riskData.mitigation_measures && riskData.mitigation_measures.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-gray-600" />
                  <h4 className="text-sm font-medium text-gray-900">Mitigation Measures</h4>
                </div>
                <ul className="space-y-1 pl-6">
                  {riskData.mitigation_measures.map((measure, measureIndex) => (
                    <li key={measureIndex} className="flex gap-2 text-sm text-gray-700">
                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                      <span>{measure}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        {(onViewDetails || onAddToWatchlist) && (
          <RiskActionButtons
            onViewDetails={onViewDetails}
            onAddToWatchlist={onAddToWatchlist}
          />
        )}
      </div>
    </div>
  )
}

function RiskActionButtons({ onViewDetails, onAddToWatchlist }: RiskActionButtonsProps) {
  return (
    <div className="mt-4 pt-3 border-t border-gray-100">
      <div className="flex items-center gap-2">
        {onViewDetails && (
          <Button
            variant="outline"
            size="sm"
            onClick={onViewDetails}
            className="text-xs"
          >
            <Info className="h-3 w-3 mr-1" />
            View Details
          </Button>
        )}
        {onAddToWatchlist && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onAddToWatchlist}
            className="text-xs"
          >
            <Shield className="h-3 w-3 mr-1" />
            Monitor Risk
          </Button>
        )}
      </div>
    </div>
  )
}

// Enhanced Risk Factor List Component
interface RiskFactorListProps {
  risks: (RiskFactor | string)[]
  title?: string
  showHeader?: boolean
  onViewRiskDetails?: (index: number) => void
  onAddRiskToWatchlist?: (index: number) => void
  className?: string
}

export function RiskFactorList({
  risks,
  title = 'Risk Factors',
  showHeader = true,
  onViewRiskDetails,
  onAddRiskToWatchlist,
  className = '',
}: RiskFactorListProps) {
  if (!risks || risks.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm">No risk factors identified</p>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {showHeader && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-error-600" />
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          </div>
          <span className="text-sm text-gray-500 font-medium">
            {risks.length} risk{risks.length !== 1 ? 's' : ''} identified
          </span>
        </div>
      )}

      <div className="space-y-3">
        {risks.map((risk, index) => (
          <RiskFactorCard
            key={index}
            risk={risk}
            index={index}
            onViewDetails={onViewRiskDetails ? () => onViewRiskDetails(index) : undefined}
            onAddToWatchlist={onAddRiskToWatchlist ? () => onAddRiskToWatchlist(index) : undefined}
          />
        ))}
      </div>
    </div>
  )
}