import React from 'react'
import {
  FileText,
  Calendar,
  Hash,
  Building,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Database,
} from 'lucide-react'
import type { FilingResponse } from '@/api/types'

interface FilingMetadataProps {
  filing: FilingResponse & {
    company_name?: string
    company_ticker?: string
  }
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
      return 'text-green-600 bg-green-50'
    case 'failed':
      return 'text-red-600 bg-red-50'
    case 'processing':
      return 'text-blue-600 bg-blue-50'
    case 'pending':
      return 'text-yellow-600 bg-yellow-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}

export const FilingMetadata: React.FC<FilingMetadataProps> = ({ filing }) => {
  const StatusIcon = getStatusIcon(filing.processing_status)
  const statusColor = getStatusColor(filing.processing_status)

  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
        <Database className="w-5 h-5" />
        <span>Filing Information</span>
      </h3>

      <div className="space-y-4">
        {/* Basic Filing Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <FileText className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Filing Type</p>
                <p className="font-medium">{filing.filing_type}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Filing Date</p>
                <p className="font-medium">{new Date(filing.filing_date).toLocaleDateString()}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Hash className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Accession Number</p>
                <p className="font-medium font-mono text-sm">{filing.accession_number}</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {(filing.company_name || filing.company_ticker) && (
              <div className="flex items-center space-x-3">
                <Building className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Company</p>
                  <p className="font-medium">
                    {filing.company_name}
                    {filing.company_ticker && ` (${filing.company_ticker})`}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Processing Status */}
        <div className="pt-4 border-t">
          <div className="flex items-center space-x-3">
            <StatusIcon className={`w-5 h-5 ${statusColor.split(' ')[0]}`} />
            <div className="flex-1">
              <p className="text-sm text-muted-foreground">Processing Status</p>
              <div className="flex items-center space-x-2 mt-1">
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${statusColor}`}
                >
                  {filing.processing_status.charAt(0).toUpperCase() +
                    filing.processing_status.slice(1)}
                </span>
              </div>
            </div>
          </div>

          {filing.processing_error && (
            <div className="mt-3 p-3 rounded-md bg-red-50 border border-red-200">
              <div className="flex items-center space-x-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <p className="text-sm font-medium text-red-800">Processing Error</p>
              </div>
              <p className="text-sm text-red-700 mt-1">{filing.processing_error}</p>
            </div>
          )}
        </div>

        {/* Analysis Summary */}
        {(filing.analyses_count !== undefined || filing.latest_analysis_date) && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-foreground mb-2">Analysis Summary</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              {filing.analyses_count !== undefined && (
                <div>
                  <p className="text-muted-foreground">Total Analyses</p>
                  <p className="font-medium">{filing.analyses_count}</p>
                </div>
              )}
              {filing.latest_analysis_date && (
                <div>
                  <p className="text-muted-foreground">Latest Analysis</p>
                  <p className="font-medium">
                    {new Date(filing.latest_analysis_date).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Additional Metadata */}
        {filing.metadata && Object.keys(filing.metadata).length > 0 && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-foreground mb-2">Additional Information</h4>
            <div className="space-y-2">
              {Object.entries(filing.metadata)
                .filter(([key]) => !['has_sections', 'section_count'].includes(key))
                .map(([key, value]) => (
                  <div key={key} className="grid grid-cols-3 gap-2 text-sm">
                    <p className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="col-span-2 font-medium break-all">
                      {value !== null ? String(value) : 'N/A'}
                    </p>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
