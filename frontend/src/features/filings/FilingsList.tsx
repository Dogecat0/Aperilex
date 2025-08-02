import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { useFilingSearch, useEdgarSearch, useFilingAnalyzeMutation } from '@/hooks/useFiling'
import { FilingSearchForm, FilingSearchResults } from './components'
import { FileText, Search } from 'lucide-react'
import type { FilingSearchParams } from '@/api/filings'
import type { CompanyResponse, EdgarSearchParams } from '@/api/types'

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
  const analyzeFiling = useFilingAnalyzeMutation()

  // Search state
  const [searchType, setSearchType] = useState<'database' | 'edgar'>('edgar')
  const [searchParams, setSearchParams] = useState<FilingSearchParams | null>(null)
  const [edgarSearchParams, setEdgarSearchParams] = useState<EdgarSearchParams | null>(null)
  const [companyData, setCompanyData] = useState<CompanyResponse | null>(null)

  // Search hooks - only enabled when we have search params
  const databaseSearchQuery = useFilingSearch(searchParams!, {
    enabled: !!searchParams && searchType === 'database',
  })

  const edgarSearchQuery = useEdgarSearch(edgarSearchParams!, {
    enabled: !!edgarSearchParams && searchType === 'edgar',
  })

  // Use the appropriate query based on search type
  const activeSearchQuery = searchType === 'edgar' ? edgarSearchQuery : databaseSearchQuery

  useEffect(() => {
    // Set breadcrumbs for the filings page
    setBreadcrumbs([
      { label: 'Dashboard', href: '/' },
      { label: 'SEC Filings', isActive: true },
    ])
  }, [setBreadcrumbs])

  const handleSearch = (params: FilingSearchParams) => {
    if (searchType === 'database') {
      setSearchParams(params)
      setEdgarSearchParams(null)
    }
    // Reset company data when searching for a new company
    if (!companyData || companyData.ticker !== params.ticker) {
      setCompanyData(null)
    }
  }

  const handleEdgarSearch = (params: EdgarSearchParams) => {
    if (searchType === 'edgar') {
      setEdgarSearchParams(params)
      setSearchParams(null)
    }
    // Reset company data when searching for a new company
    if (!companyData || companyData.ticker !== params.ticker) {
      setCompanyData(null)
    }
  }

  const handleSearchTypeChange = (newType: 'database' | 'edgar') => {
    setSearchType(newType)
    // Clear search params when switching types
    setSearchParams(null)
    setEdgarSearchParams(null)
    setCompanyData(null)
  }

  const handlePageChange = (page: number) => {
    if (searchType === 'edgar' && edgarSearchParams) {
      setEdgarSearchParams({ ...edgarSearchParams, page })
    } else if (searchType === 'database' && searchParams) {
      setSearchParams({ ...searchParams, page })
    }
  }

  const handleViewDetails = (accessionNumber: string) => {
    navigate(`/filings/${accessionNumber}`)
  }

  const handleAnalyze = async (accessionNumber: string) => {
    try {
      await analyzeFiling.mutateAsync({
        accessionNumber,
        options: { analysis_type: 'COMPREHENSIVE' },
      })
      // The mutation will handle cache invalidation and show success feedback
    } catch (error) {
      console.error('Failed to start analysis:', error)
      // TODO: Show error toast notification
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold flex items-center space-x-2">
          <FileText className="w-8 h-8" />
          <span>SEC Filing Search</span>
        </h1>
        <p className="text-muted-foreground">
          Search and analyze SEC filings for any public company. Enter a ticker symbol to get
          started.
        </p>
      </div>

      {/* Search Form */}
      <FilingSearchForm
        onSearch={handleSearch}
        onEdgarSearch={handleEdgarSearch}
        isLoading={activeSearchQuery.isLoading}
        searchType={searchType}
        onSearchTypeChange={handleSearchTypeChange}
      />

      {/* Welcome State (No Search Yet) */}
      {!searchParams && !edgarSearchParams && (
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
                    if (searchType === 'edgar') {
                      handleEdgarSearch({ ticker, page: 1, page_size: 20 })
                    } else {
                      handleSearch({ ticker, page: 1, page_size: 20 })
                    }
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
      {(searchParams || edgarSearchParams) && (
        <FilingSearchResults
          data={activeSearchQuery.data}
          isLoading={activeSearchQuery.isLoading}
          error={activeSearchQuery.error as any}
          onViewDetails={handleViewDetails}
          onAnalyze={handleAnalyze}
          onPageChange={handlePageChange}
          companyName={companyData?.display_name}
          searchTicker={searchType === 'edgar' ? edgarSearchParams?.ticker : searchParams?.ticker}
          resultType={searchType}
        />
      )}
    </div>
  )
}
