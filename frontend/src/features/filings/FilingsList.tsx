import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { useFilingAnalyzeMutation } from '@/hooks/useFiling'
import { FilingCard } from './components/FilingCard'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { AlertCircle, FileText, Search, Filter, RefreshCw, Building } from 'lucide-react'
import type { FilingResponse } from '@/api/types'

interface FilingsListProps {
  filings?: FilingResponse[]
  isLoading?: boolean
  error?: any
  companyTicker?: string
  companyName?: string
  showCompanyInfo?: boolean
  onRefresh?: () => void
}

export function FilingsList({
  filings = [],
  isLoading = false,
  error,
  companyTicker,
  companyName,
  showCompanyInfo = true,
  onRefresh,
}: FilingsListProps) {
  const navigate = useNavigate()
  const { setBreadcrumbs } = useAppStore()
  const analyzeFiling = useFilingAnalyzeMutation()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')

  // Filter filings based on search and status filter
  const filteredFilings = React.useMemo(() => {
    return filings.filter((filing) => {
      const matchesSearch =
        !searchTerm ||
        filing.filing_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        filing.accession_number.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = filterStatus === 'all' || filing.processing_status === filterStatus

      return matchesSearch && matchesStatus
    })
  }, [filings, searchTerm, filterStatus])

  React.useEffect(() => {
    if (companyTicker && companyName) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Companies', href: '/companies' },
        { label: companyName, href: `/companies/${companyTicker}` },
        { label: 'Filings', isActive: true },
      ])
    } else {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Filings', isActive: true },
      ])
    }
  }, [companyTicker, companyName, setBreadcrumbs])

  const handleViewDetails = (accessionNumber: string) => {
    navigate(`/filings/${accessionNumber}`)
  }

  const handleAnalyze = async (accessionNumber: string) => {
    try {
      await analyzeFiling.mutateAsync({
        accessionNumber,
        options: { analysis_type: 'COMPREHENSIVE' },
      })
      // The mutation will handle cache invalidation
    } catch (error) {
      console.error('Failed to start analysis:', error)
      // TODO: Show error toast
    }
  }

  const statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'completed', label: 'Completed' },
    { value: 'processing', label: 'Processing' },
    { value: 'pending', label: 'Pending' },
    { value: 'failed', label: 'Failed' },
  ]

  if (error) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {companyTicker ? `${companyName} Filings` : 'SEC Filings'}
            </h1>
            <p className="text-muted-foreground">
              {companyTicker
                ? `SEC filings for ${companyName} (${companyTicker})`
                : 'Browse and analyze SEC filings'}
            </p>
          </div>
          {onRefresh && (
            <Button variant="outline" onClick={onRefresh}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          )}
        </div>

        {/* Error State */}
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <div>
              <h3 className="font-medium text-destructive">Failed to Load Filings</h3>
              <p className="text-sm text-muted-foreground mt-1">
                There was an error loading the filings. Please try again.
              </p>
            </div>
          </div>
          {onRefresh && (
            <Button variant="outline" onClick={onRefresh} className="mt-4">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center space-x-2">
            {companyTicker && <Building className="w-6 h-6" />}
            <span>{companyTicker ? `${companyName} Filings` : 'SEC Filings'}</span>
          </h1>
          <p className="text-muted-foreground">
            {companyTicker
              ? `SEC filings for ${companyName} (${companyTicker})`
              : 'Browse and analyze SEC filings'}
          </p>
        </div>
        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search filings by type or accession number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          {[...Array(5)].map((_, index) => (
            <Skeleton key={index} className="h-32 w-full" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredFilings.length === 0 && !error && (
        <div className="text-center py-12">
          <FileText className="mx-auto w-12 h-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">
            {searchTerm || filterStatus !== 'all' ? 'No Matching Filings' : 'No Filings Available'}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {searchTerm || filterStatus !== 'all'
              ? 'Try adjusting your search or filter criteria.'
              : companyTicker
                ? `No filings found for ${companyName}.`
                : 'No SEC filings are currently available.'}
          </p>
          {(searchTerm || filterStatus !== 'all') && (
            <Button
              variant="outline"
              onClick={() => {
                setSearchTerm('')
                setFilterStatus('all')
              }}
            >
              Clear Filters
            </Button>
          )}
        </div>
      )}

      {/* Filings List */}
      {!isLoading && filteredFilings.length > 0 && (
        <div className="space-y-4">
          {/* Results Summary */}
          <div className="text-sm text-muted-foreground">
            Showing {filteredFilings.length} of {filings.length} filing
            {filings.length !== 1 ? 's' : ''}
          </div>

          {/* Filing Cards */}
          <div className="space-y-4">
            {filteredFilings.map((filing) => (
              <FilingCard
                key={filing.filing_id}
                filing={{
                  ...filing,
                  company_name: companyName,
                  company_ticker: companyTicker,
                }}
                onViewDetails={handleViewDetails}
                onAnalyze={handleAnalyze}
                showCompanyInfo={showCompanyInfo}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
