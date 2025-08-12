import type { FC } from 'react'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { FilingCard } from './FilingCard'
import {
  ChevronLeft,
  ChevronRight,
  FileText,
} from 'lucide-react'
import type { FilingResponse, PaginatedResponse } from '@/api/types'

interface FilingSearchResultsProps {
  data?: PaginatedResponse<FilingResponse>
  isLoading?: boolean
  error?: any
  onViewDetails?: (accessionNumber: string) => void
  onAnalyze?: (accessionNumber: string) => void
  onPageChange?: (page: number) => void
  companyName?: string
  searchTicker?: string
}


export const FilingSearchResults: FC<FilingSearchResultsProps> = ({
  data,
  isLoading,
  error,
  onViewDetails,
  onAnalyze,
  onPageChange,
  companyName,
  searchTicker,
}) => {
  if (error) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-destructive" />
          <div>
            <h3 className="font-medium text-destructive">Search Failed</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {error?.detail || 'There was an error searching for filings. Please try again.'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-6 w-32" />
        </div>
        {[...Array(5)].map((_, index) => (
          <Skeleton key={index} className="h-32 w-full" />
        ))}
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="mx-auto w-12 h-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No Filings Found</h3>
        <p className="text-sm text-muted-foreground mb-4">
          {searchTicker
            ? `No SEC filings found for ${searchTicker}. Try adjusting your search criteria.`
            : 'No SEC filings match your search criteria. Try adjusting your filters.'}
        </p>
      </div>
    )
  }

  const { items: filings, pagination } = data

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">
            {companyName ? `${companyName} Filings` : `${searchTicker} Filings`}
          </h2>
          <p className="text-sm text-muted-foreground">
            Showing {pagination.total_items} filing{pagination.total_items !== 1 ? 's' : ''}{' '}
            {pagination.total_pages > 1 && (
              <>
                (page {pagination.page} of {pagination.total_pages})
              </>
            )}
          </p>
        </div>

        {/* Page Info */}
        {pagination.total_pages > 1 && (
          <div className="text-sm text-muted-foreground">
            {(pagination.page - 1) * pagination.page_size + 1}-
            {Math.min(pagination.page * pagination.page_size, pagination.total_items)} of{' '}
            {pagination.total_items}
          </div>
        )}
      </div>

      {/* Filing Cards */}
      <div className="space-y-4">
        {(filings as FilingResponse[]).map((filing) => (
          <FilingCard
            key={filing.filing_id}
            filing={{
              ...filing,
              company_name: companyName,
              company_ticker: searchTicker,
            }}
            onViewDetails={onViewDetails}
            onAnalyze={onAnalyze}
            showCompanyInfo={false} // Hide company info since we're searching for a specific company
          />
        ))}
      </div>

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange?.(pagination.page - 1)}
              disabled={!pagination.has_previous}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>

            <div className="flex items-center space-x-1">
              {/* Show page numbers */}
              {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                let pageNum: number

                if (pagination.total_pages <= 5) {
                  pageNum = i + 1
                } else if (pagination.page <= 3) {
                  pageNum = i + 1
                } else if (pagination.page >= pagination.total_pages - 2) {
                  pageNum = pagination.total_pages - 4 + i
                } else {
                  pageNum = pagination.page - 2 + i
                }

                const isCurrentPage = pageNum === pagination.page

                return (
                  <Button
                    key={pageNum}
                    variant={isCurrentPage ? 'primary' : 'outline'}
                    size="sm"
                    onClick={() => onPageChange?.(pageNum)}
                    className="w-8 h-8 p-0"
                  >
                    {pageNum}
                  </Button>
                )
              })}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange?.(pagination.page + 1)}
              disabled={!pagination.has_next}
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            Page {pagination.page} of {pagination.total_pages}
          </div>
        </div>
      )}
    </div>
  )
}
