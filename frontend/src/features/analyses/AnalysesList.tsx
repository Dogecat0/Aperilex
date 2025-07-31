import { useState } from 'react'
import { Search, Filter, ChevronDown, TrendingUp } from 'lucide-react'
import { useAnalyses } from '@/hooks/useAnalysis'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { AnalysisCard } from './components/AnalysisCard'
import type { AnalysisType, ListAnalysesParams } from '@/api/types'

export function AnalysesList() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<ListAnalysesParams>({
    page: 1,
    page_size: 20,
  })
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading, error } = useAnalyses(filters)

  const handleSearch = (term: string) => {
    setSearchTerm(term)
    setFilters((prev) => ({
      ...prev,
      page: 1,
      // Note: The API doesn't have a search parameter, but we could filter by ticker
      ticker: term.length > 0 ? term.toUpperCase() : undefined,
    }))
  }

  const handleFilterChange = (key: keyof ListAnalysesParams, value: any) => {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      [key]: value,
    }))
  }

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }

  const analysisTypes: { value: AnalysisType; label: string }[] = [
    { value: 'COMPREHENSIVE', label: 'Comprehensive' },
    { value: 'FINANCIAL_FOCUSED', label: 'Financial Focused' },
    { value: 'RISK_FOCUSED', label: 'Risk Focused' },
    { value: 'BUSINESS_FOCUSED', label: 'Business Focused' },
  ]

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-error-50 border border-error-200 rounded-lg p-4">
          <h3 className="text-error-800 font-medium">Error loading analyses</h3>
          <p className="text-error-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analysis Library</h1>
            <p className="text-gray-600 mt-1">
              Browse and explore all financial analyses across companies and filings
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <TrendingUp className="h-4 w-4" />
            <span>{data?.pagination.total_items || 0} total analyses</span>
          </div>
        </div>

        {/* Search and Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search by company ticker (e.g., AAPL, MSFT)..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2"
          >
            <Filter className="h-4 w-4" />
            Filters
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
            />
          </Button>
        </div>

        {/* Expandable Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Analysis Type
                </label>
                <select
                  value={filters.analysis_type || ''}
                  onChange={(e) => handleFilterChange('analysis_type', e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">All Types</option>
                  {analysisTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
                <Input
                  type="date"
                  value={filters.start_date || ''}
                  onChange={(e) => handleFilterChange('start_date', e.target.value || undefined)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
                <Input
                  type="date"
                  value={filters.end_date || ''}
                  onChange={(e) => handleFilterChange('end_date', e.target.value || undefined)}
                />
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFilters({ page: 1, page_size: 20 })
                  setSearchTerm('')
                }}
              >
                Clear Filters
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg border shadow-sm p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="h-6 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="flex gap-2 mb-4">
                <div className="h-6 w-20 bg-gray-200 rounded"></div>
                <div className="h-6 w-16 bg-gray-200 rounded"></div>
              </div>
              <div className="h-4 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      )}

      {/* Analysis Grid */}
      {data && !isLoading && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {data.items.map((analysis) => (
              <AnalysisCard key={analysis.analysis_id} analysis={analysis} />
            ))}
          </div>

          {/* Empty State */}
          {data.items.length === 0 && (
            <div className="text-center py-12">
              <div className="bg-gray-100 rounded-full p-3 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <TrendingUp className="h-8 w-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No analyses found</h3>
              <p className="text-gray-500 mb-4">
                Try adjusting your search criteria or filters to find more analyses.
              </p>
            </div>
          )}

          {/* Pagination */}
          {data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Showing {(data.pagination.page - 1) * data.pagination.page_size + 1} to{' '}
                {Math.min(
                  data.pagination.page * data.pagination.page_size,
                  data.pagination.total_items
                )}{' '}
                of {data.pagination.total_items} analyses
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!data.pagination.has_previous}
                  onClick={() =>
                    data.pagination.previous_page && handlePageChange(data.pagination.previous_page)
                  }
                >
                  Previous
                </Button>
                <span className="px-3 py-2 text-sm font-medium">
                  Page {data.pagination.page} of {data.pagination.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!data.pagination.has_next}
                  onClick={() =>
                    data.pagination.next_page && handlePageChange(data.pagination.next_page)
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
