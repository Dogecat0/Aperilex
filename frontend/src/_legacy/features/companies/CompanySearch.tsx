import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { CompanyCard } from './components/CompanyCard'
import { useCompany } from '@/hooks/useCompany'
import { Search, Loader2, AlertCircle } from 'lucide-react'

interface CompanySearchProps {
  onCompanySelect?: (ticker: string) => void
  showAnalyses?: boolean
}

export const CompanySearch = React.forwardRef<HTMLDivElement, CompanySearchProps>(
  ({ onCompanySelect, showAnalyses = false }, ref) => {
    const navigate = useNavigate()
    const [searchTerm, setSearchTerm] = useState('')
    const [searchedTicker, setSearchedTicker] = useState<string | null>(null)

    // Only make the API call when searchedTicker is set
    const {
      data: company,
      isLoading,
      error,
      refetch,
    } = useCompany(searchedTicker || '', {
      includeRecentAnalyses: showAnalyses,
      enabled: !!searchedTicker,
    })

    const handleSearch = (e: React.FormEvent) => {
      e.preventDefault()
      if (searchTerm.trim()) {
        setSearchedTicker(searchTerm.trim().toUpperCase())
      }
    }

    const handleCompanySelect = (ticker: string) => {
      if (onCompanySelect) {
        onCompanySelect(ticker)
      } else {
        // Default behavior: navigate to company profile
        navigate(`/companies/${ticker}`)
      }
    }

    const clearSearch = () => {
      setSearchTerm('')
      setSearchedTicker(null)
    }

    return (
      <div ref={ref} className="space-y-6">
        {/* Search Form */}
        <div className="rounded-lg border bg-card p-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <h2 className="text-lg font-semibold">Search Companies</h2>
              <p className="text-sm text-muted-foreground">
                Enter a company ticker symbol to search for company information and analysis
              </p>
            </div>

            <form onSubmit={handleSearch} className="flex space-x-2">
              <div className="flex-1">
                <Input
                  type="text"
                  placeholder="Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="uppercase"
                />
              </div>
              <Button type="submit" disabled={!searchTerm.trim() || isLoading}>
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                <span className="ml-2">Search</span>
              </Button>
            </form>

            {searchedTicker && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Searching for: <span className="font-medium">{searchedTicker}</span>
                </span>
                <Button variant="ghost" size="sm" onClick={clearSearch}>
                  Clear
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Search Results */}
        {searchedTicker && (
          <div className="space-y-4">
            {isLoading && (
              <div className="rounded-lg border bg-card p-6">
                <div className="flex items-center justify-center space-x-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="text-muted-foreground">Searching for company...</span>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-5 h-5 text-destructive" />
                  <div>
                    <h3 className="font-medium text-destructive">Company not found</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Could not find a company with ticker "{searchedTicker}". Please check the
                      spelling and try again.
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-3">
                  Try Again
                </Button>
              </div>
            )}

            {company && !isLoading && !error && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Search Results</h3>
                  <span className="text-sm text-muted-foreground">1 company found</span>
                </div>
                <CompanyCard
                  company={company}
                  onViewProfile={handleCompanySelect}
                  showAnalyses={showAnalyses}
                  ticker={searchedTicker}
                />
              </div>
            )}
          </div>
        )}

        {/* Help Section */}
        {!searchedTicker && (
          <div className="rounded-lg border bg-muted/30 p-6">
            <div className="space-y-2">
              <h3 className="font-medium">How to search</h3>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>• Enter a valid stock ticker symbol (e.g., AAPL for Apple Inc.)</p>
                <p>• Ticker symbols are typically 1-5 characters long</p>
                <p>• Search is case-insensitive</p>
                <p>• Only companies with SEC filings can be found</p>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <h4 className="text-sm font-medium">Popular examples:</h4>
              <div className="flex flex-wrap gap-2">
                {['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META'].map((ticker) => (
                  <Button
                    key={ticker}
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearchTerm(ticker)
                      setSearchedTicker(ticker)
                    }}
                    className="text-xs"
                  >
                    {ticker}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
)

CompanySearch.displayName = 'CompanySearch'
