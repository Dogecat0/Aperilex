import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { useFilingSearch } from '@/hooks/useFiling'
import { FilingSearchForm, FilingSearchResults } from './components'
import { Search } from 'lucide-react'
import type { FilingSearchParams } from '@/api/filings'
import type { CompanyResponse } from '@/api/types'

interface FilingsListProps {
  // Legacy props for backward compatibility (unused in new implementation)
  filings?: never
  isLoading?: never
  error?: never
  companyTicker?: never
  companyName?: never
  showCompanyInfo?: never
  onRefresh?: never
}

export function FilingsList(_props: FilingsListProps) {
  const navigate = useNavigate()
  const { setBreadcrumbs } = useAppStore()

  // Search state
  const [searchParams, setSearchParams] = useState<FilingSearchParams | null>(null)
  const [companyData, setCompanyData] = useState<CompanyResponse | null>(null)

  // Search hooks - only enabled when we have search params
  const databaseSearchQuery = useFilingSearch(searchParams!, {
    enabled: !!searchParams,
  })

  useEffect(() => {
    // Set breadcrumbs for the filings page
    setBreadcrumbs([
      { label: 'Dashboard', href: '/' },
      { label: 'SEC Filings', isActive: true },
    ])
  }, [setBreadcrumbs])

  const handleSearch = (params: FilingSearchParams) => {
    setSearchParams(params)
    // Reset company data when searching for a new company
    if (!companyData || companyData.ticker !== params.ticker) {
      setCompanyData(null)
    }
  }

  const handlePageChange = (page: number) => {
    if (searchParams) {
      setSearchParams({ ...searchParams, page })
    }
  }

  const handleViewDetails = (accessionNumber: string) => {
    navigate(`/filings/${accessionNumber}`)
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold flex items-center space-x-2">
          <span>SEC Filing Search</span>
        </h1>
        <p className="text-muted-foreground">
          Search and analyze SEC filings for any public company. Enter a ticker symbol to get
          started.
        </p>
      </div>

      {/* Search Form */}
      <FilingSearchForm onSearch={handleSearch} isLoading={databaseSearchQuery.isLoading} />

      {/* Welcome State (No Search Yet) */}
      {!searchParams && (
        <div className="text-center py-16">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
            <Search className="w-8 h-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Find SEC Filings</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            Enter a company ticker symbol above to search through their SEC filings. You can filter
            by filing type and date range to find exactly what you need.
          </p>
          <div className="mt-6 space-y-2">
            <p className="text-sm text-muted-foreground">Popular searches:</p>
            <div className="flex justify-center space-x-2">
              {['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'].map((ticker) => (
                <button
                  key={ticker}
                  onClick={() => {
                    handleSearch({ ticker, page: 1, page_size: 20 })
                  }}
                  className="px-3 py-1 text-xs bg-muted hover:bg-muted/80 rounded-full transition-colors"
                >
                  {ticker}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      {searchParams && (
        <FilingSearchResults
          data={databaseSearchQuery.data}
          isLoading={databaseSearchQuery.isLoading}
          error={databaseSearchQuery.error as any}
          onViewDetails={handleViewDetails}
          onPageChange={handlePageChange}
          companyName={companyData?.display_name}
          searchTicker={searchParams?.ticker}
        />
      )}
    </div>
  )
}
