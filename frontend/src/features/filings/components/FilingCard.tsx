import React from 'react'
import { Button } from '@/components/ui/Button'
import {
  FileText,
  Calendar,
  Building,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  BarChart3,
  Play,
} from 'lucide-react'
import type { FilingResponse } from '@/api/types'
import { useFilingHasAnalysis } from '@/hooks/useFilingAnalysisStatus'

interface FilingCardProps {
  filing: FilingResponse & {
    has_analysis?: boolean
    analysis_date?: string
    company_name?: string
    company_ticker?: string
  }
  onViewDetails?: (accessionNumber: string) => void
  onAnalyze?: (accessionNumber: string) => void
  showCompanyInfo?: boolean
}

const FILING_TYPE_ICONS = {
  '10-K': FileText,
  '10-Q': FileText,
  '8-K': FileText,
  'DEF 14A': FileText,
  '10-K/A': FileText,
  '10-Q/A': FileText,
} as const

const getFilingTypeIcon = (filingType: string) => {
  return FILING_TYPE_ICONS[filingType as keyof typeof FILING_TYPE_ICONS] || FileText
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return CheckCircle
    case 'failed':
      return XCircle
    case 'processing':
      return Clock
    case 'pending':
      return AlertCircle
    default:
      return AlertCircle
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'text-green-600'
    case 'failed':
      return 'text-red-600'
    case 'processing':
      return 'text-blue-600'
    case 'pending':
      return 'text-yellow-600'
    default:
      return 'text-gray-600'
  }
}

export const FilingCard = React.forwardRef<HTMLDivElement, FilingCardProps>(
  ({ filing, onViewDetails, onAnalyze, showCompanyInfo = true }, ref) => {
    const FilingTypeIcon = getFilingTypeIcon(filing.filing_type)
    const StatusIcon = getStatusIcon(filing.processing_status)
    const statusColor = getStatusColor(filing.processing_status)

    // Use frontend hook to check analysis status (workaround for backend issue)
    const { data: analysisStatus, isLoading: analysisLoading } = useFilingHasAnalysis(filing.filing_id)
    const hasAnalysis = analysisStatus?.hasAnalysis || filing.has_analysis || (filing.analyses_count && filing.analyses_count > 0)

    const handleViewDetails = () => {
      if (onViewDetails) {
        onViewDetails(filing.accession_number)
      }
    }

    const handleAnalyze = () => {
      if (onAnalyze) {
        onAnalyze(filing.accession_number)
      }
    }

    return (
      <div
        ref={ref}
        className="rounded-lg border bg-card p-6 space-y-4 hover:shadow-md transition-shadow"
      >
        {/* Filing Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <FilingTypeIcon className="w-5 h-5 text-primary" />
              <div>
                <h3 className="text-lg font-semibold text-foreground">{filing.filing_type}</h3>
                <p className="text-sm text-muted-foreground">{filing.accession_number}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {onViewDetails && (
              <Button variant="outline" size="sm" onClick={handleViewDetails}>
                View Details
              </Button>
            )}
            {onAnalyze && !hasAnalysis && !analysisLoading && (
              <Button size="sm" onClick={handleAnalyze}>
                <Play className="w-4 h-4 mr-2" />
                Analyze
              </Button>
            )}
          </div>
        </div>

        {/* Company Info */}
        {showCompanyInfo && (filing.company_name || filing.company_ticker) && (
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Building className="w-4 h-4" />
            <span>
              {filing.company_name}
              {filing.company_ticker && ` (${filing.company_ticker})`}
            </span>
          </div>
        )}

        {/* Filing Details */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Calendar className="w-4 h-4" />
            <span>Filed: {new Date(filing.filing_date).toLocaleDateString()}</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-sm">
              <StatusIcon className={`w-4 h-4 ${statusColor}`} />
              <span className="text-muted-foreground">
                Processing:{' '}
                <span className={statusColor.replace('text-', 'text-')}>
                  {filing.processing_status}
                </span>
              </span>
            </div>

            {hasAnalysis && (
              <div className="flex items-center space-x-2 text-sm text-green-600">
                <BarChart3 className="w-4 h-4" />
                <span>Analysis Available</span>
              </div>
            )}
          </div>

          {filing.processing_error && (
            <div className="text-sm text-red-600 bg-red-50 p-2 rounded-md">
              <div className="flex items-center space-x-1">
                <XCircle className="w-4 h-4" />
                <span className="font-medium">Processing Error:</span>
              </div>
              <p className="mt-1 text-xs">{filing.processing_error}</p>
            </div>
          )}
        </div>

        {/* Analysis Information */}
        {hasAnalysis && (filing.analysis_date || filing.latest_analysis_date) && (
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center space-x-2 text-muted-foreground">
                <BarChart3 className="w-4 h-4" />
                <span>
                  Last Analysis:{' '}
                  {new Date(
                    filing.analysis_date || filing.latest_analysis_date!
                  ).toLocaleDateString()}
                </span>
              </div>
              {filing.analyses_count && filing.analyses_count > 0 && (
                <span className="text-xs text-muted-foreground">
                  {filing.analyses_count} analysis{filing.analyses_count > 1 ? 'es' : ''}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }
)

FilingCard.displayName = 'FilingCard'
