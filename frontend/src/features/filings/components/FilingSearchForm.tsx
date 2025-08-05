import React, { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Search, Filter, Calendar, FileText, X, Database, Globe } from 'lucide-react'
import type { FilingSearchParams } from '@/api/filings'
import type { EdgarSearchParams } from '@/api/types'

type SearchType = 'database' | 'edgar'

interface FilingSearchFormProps {
  onSearch: (params: FilingSearchParams) => void
  onEdgarSearch?: (params: EdgarSearchParams) => void
  isLoading?: boolean
  initialValues?: Partial<FilingSearchParams>
  searchType?: SearchType
  onSearchTypeChange?: (type: SearchType) => void
}

const FILING_TYPES = [
  { value: '', label: 'All Filing Types' },
  { value: '10-K', label: '10-K (Annual Report)' },
  { value: '10-Q', label: '10-Q (Quarterly Report)' },
]

export function FilingSearchForm({
  onSearch,
  onEdgarSearch,
  isLoading = false,
  initialValues = {},
  searchType = 'edgar',
  onSearchTypeChange,
}: FilingSearchFormProps) {
  const [ticker, setTicker] = useState(initialValues.ticker || '')
  const [filingType, setFilingType] = useState(initialValues.filing_type || '')
  const [startDate, setStartDate] = useState(initialValues.start_date || '')
  const [endDate, setEndDate] = useState(initialValues.end_date || '')
  const [showAdvanced, setShowAdvanced] = useState(
    !!(initialValues.filing_type || initialValues.start_date || initialValues.end_date)
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!ticker.trim()) {
      return
    }

    if (searchType === 'edgar' && onEdgarSearch) {
      const params: EdgarSearchParams = {
        ticker: ticker.trim().toUpperCase(),
        page: 1,
        page_size: 20,
      }

      if (filingType) {
        params.form_type = filingType
      }

      if (startDate) {
        params.date_from = startDate
      }

      if (endDate) {
        params.date_to = endDate
      }

      onEdgarSearch(params)
    } else {
      const params: FilingSearchParams = {
        ticker: ticker.trim().toUpperCase(),
        page: 1,
        page_size: 20,
      }

      if (filingType) {
        params.filing_type = filingType
      }

      if (startDate) {
        params.start_date = startDate
      }

      if (endDate) {
        params.end_date = endDate
      }

      onSearch(params)
    }
  }

  const handleClear = () => {
    setTicker('')
    setFilingType('')
    setStartDate('')
    setEndDate('')
    setShowAdvanced(false)
  }

  const hasFilters = filingType || startDate || endDate

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Search Type Selector */}
      {onSearchTypeChange && (
        <div className="flex items-center gap-4 p-3 bg-muted/30 rounded-lg border">
          <span className="text-sm font-medium">Search in:</span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={searchType === 'edgar' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => onSearchTypeChange('edgar')}
              className="text-xs"
            >
              <Globe className="w-3 h-3 mr-1" />
              SEC Edgar (All Filings)
            </Button>
            <Button
              type="button"
              variant={searchType === 'database' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => onSearchTypeChange('database')}
              className="text-xs"
            >
              <Database className="w-3 h-3 mr-1" />
              Our Database (Processed)
            </Button>
          </div>
        </div>
      )}

      {/* Main Search Row */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Enter company ticker (e.g., AAPL, MSFT, GOOGL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="pl-10"
              required
            />
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="whitespace-nowrap"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {hasFilters && (
              <span className="ml-2 bg-primary text-primary-foreground rounded-full px-2 py-0.5 text-xs">
                {[filingType, startDate, endDate].filter(Boolean).length}
              </span>
            )}
          </Button>
          <Button type="submit" disabled={isLoading || !ticker.trim()}>
            <Search className="w-4 h-4 mr-2" />
            {isLoading ? 'Searching...' : 'Search'}
          </Button>
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="border rounded-lg p-4 space-y-4 bg-muted/50">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium flex items-center">
              <Filter className="w-4 h-4 mr-2" />
              Advanced Filters
            </h3>
            {hasFilters && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleClear}
                className="text-xs"
              >
                <X className="w-3 h-3 mr-1" />
                Clear All
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Filing Type Filter */}
            <div className="space-y-2">
              <label htmlFor="filing-type" className="text-sm font-medium flex items-center">
                <FileText className="w-4 h-4 mr-2" />
                Filing Type
              </label>
              <select
                id="filing-type"
                value={filingType}
                onChange={(e) => setFilingType(e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {FILING_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Start Date Filter */}
            <div className="space-y-2">
              <label htmlFor="start-date" className="text-sm font-medium flex items-center">
                <Calendar className="w-4 h-4 mr-2" />
                From Date
              </label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                max={endDate || undefined}
              />
            </div>

            {/* End Date Filter */}
            <div className="space-y-2">
              <label htmlFor="end-date" className="text-sm font-medium flex items-center">
                <Calendar className="w-4 h-4 mr-2" />
                To Date
              </label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate || undefined}
                max={new Date().toISOString().split('T')[0]}
              />
            </div>
          </div>

          {/* Active Filters Display */}
          {hasFilters && (
            <div className="pt-2 border-t">
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground">Active filters:</span>
                {filingType && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    Type: {filingType}
                    <button
                      type="button"
                      onClick={() => setFilingType('')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {startDate && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    From: {startDate}
                    <button
                      type="button"
                      onClick={() => setStartDate('')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {endDate && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    To: {endDate}
                    <button
                      type="button"
                      onClick={() => setEndDate('')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </form>
  )
}
