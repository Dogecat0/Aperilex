import React, { useState, useMemo, useCallback } from 'react'
import {
  Search,
  AlertCircle,
  Filter,
  Bookmark,
  Building,
  Shield,
  DollarSign,
  Layers,
  Eye,
  SlidersHorizontal,
  X,
  ChevronUp,
  ChevronDown,
} from 'lucide-react'
import { RiskFactorList } from './RiskFactorCard'
import { FinancialMetricsGrid } from './FinancialMetricsGrid'
import { SectionHeader, getAnalysisType, extractSectionMetadata } from './SectionHeader'
import { AnalysisSummaryCard } from '@/components/analysis/AnalysisSummaryCard'
import { Button } from '@/components/ui/Button'
import {
  type ContentCategory,
  type FilterType,
  processAnalysisData,
  getFilteredContent,
  hasSpecializedContent,
  formatKey,
} from '@/utils/analysisHelpers'
import { ContentRenderer } from './ContentRenderer'

interface GenericAnalysisSectionProps {
  analysis: any
  schemaType: string
  loading?: boolean
  onExport?: () => void
  onShare?: () => void
  onBookmark?: () => void
  className?: string
}

export function GenericAnalysisSection({
  analysis,
  schemaType,
  loading = false,
  onExport,
  onShare,
  onBookmark,
  className = '',
}: GenericAnalysisSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [activeTab, setActiveTab] = useState<ContentCategory | 'all'>('all')
  const [showFilters, setShowFilters] = useState(false)

  // Memoized data processing
  const processedData = useMemo(
    () => processAnalysisData(analysis, searchTerm),
    [analysis, searchTerm]
  )

  // Memoized filtered content
  const filteredContent = useMemo(
    () => getFilteredContent(processedData, activeTab, activeFilter),
    [processedData, activeTab, activeFilter]
  )

  // Callbacks to reduce re-renders
  const clearSearch = useCallback(() => setSearchTerm(''), [])
  const showAll = useCallback(() => setActiveFilter('all'), [])

  // Enhanced rendering for specialized content
  const renderSpecializedContent = useCallback(
    (analysisData: any): React.ReactNode | null => {
      if (!hasSpecializedContent(analysisData)) return null

      // Financial metrics (single metric or array)
      if (analysisData.metric_name && (analysisData.current_value || analysisData.previous_value)) {
        return (
          <FinancialMetricsGrid
            metrics={[analysisData]}
            title="Financial Metrics"
            showComparisons={true}
            highlightSignificant={true}
            maxDisplayCount={6}
            loading={loading}
          />
        )
      }

      if (Array.isArray(analysisData) && analysisData.length > 0 && analysisData[0].metric_name) {
        return (
          <FinancialMetricsGrid
            metrics={analysisData}
            title="Financial Metrics"
            showComparisons={true}
            highlightSignificant={true}
            maxDisplayCount={6}
            loading={loading}
          />
        )
      }

      // Risk factors
      if (Array.isArray(analysisData) && analysisData.length > 0 && analysisData[0].risk_name) {
        return <RiskFactorList risks={analysisData} showHeader={false} />
      }

      // Key financial metrics from nested structures
      if (analysisData.key_financial_metrics && Array.isArray(analysisData.key_financial_metrics)) {
        return (
          <FinancialMetricsGrid
            metrics={analysisData.key_financial_metrics}
            title="Key Financial Metrics"
            showComparisons={true}
            highlightSignificant={true}
            loading={loading}
          />
        )
      }

      // Risk factors from nested structures
      if (analysisData.risk_factors && Array.isArray(analysisData.risk_factors)) {
        return <RiskFactorList risks={analysisData.risk_factors} showHeader={false} />
      }

      return null
    },
    [loading]
  )

  // Check for specialized content rendering
  const specializedContent = useMemo(
    () => renderSpecializedContent(analysis),
    [analysis, renderSpecializedContent]
  )

  // Analysis type and metadata
  const analysisType = getAnalysisType(schemaType)
  const metadata = extractSectionMetadata(analysis)

  // Loading state
  if (loading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="animate-pulse">
          <div className="bg-gray-200 h-16 rounded-lg mb-4"></div>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-gray-200 h-24 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (!analysis || typeof analysis !== 'object') {
    return (
      <div
        className={`flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}
      >
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
        <div>
          <h3 className="font-medium text-red-900">Invalid Analysis Data</h3>
          <p className="text-sm text-red-700 mt-1">
            Unable to display analysis for schema type: {schemaType}
          </p>
        </div>
      </div>
    )
  }

  // Render specialized content if available
  if (specializedContent) {
    return (
      <div className={`space-y-6 ${className}`}>
        {/* Enhanced Section Header */}
        <SectionHeader
          title={formatKey(schemaType.replace(/([A-Z])/g, ' $1').trim())}
          subtitle="Specialized analysis view with enhanced visualizations"
          analysisType={analysisType}
          size="md"
          isExpanded={isExpanded}
          onToggle={() => setIsExpanded(!isExpanded)}
          metadata={{
            ...metadata,
            totalSections: processedData.totalSections,
          }}
          quickActions={{
            showExport: Boolean(onExport),
            showShare: Boolean(onShare),
            onExport,
            onShare,
            customActions: onBookmark
              ? [
                  {
                    icon: Bookmark,
                    label: 'Bookmark',
                    onClick: onBookmark,
                  },
                ]
              : undefined,
          }}
        />

        {/* Specialized content */}
        {isExpanded && <div className="space-y-4">{specializedContent}</div>}

        {/* Debug info (development only) */}
        {process.env.NODE_ENV === 'development' && (
          <details className="text-xs">
            <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
              Debug: Schema & Processing Info
            </summary>
            <div className="mt-2 p-3 bg-gray-100 rounded font-mono text-gray-600 text-xs">
              <div>Schema: {schemaType}</div>
              <div>Analysis Type: {analysisType}</div>
              <div>Total Items: {processedData.totalSections}</div>
              <div>Has Financial: {processedData.hasFinancialData.toString()}</div>
              <div>Has Risk Data: {processedData.hasRiskData.toString()}</div>
              <div>Has Business Data: {processedData.hasBusinessData.toString()}</div>
            </div>
          </details>
        )}
      </div>
    )
  }

  // Generic categorized rendering
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Enhanced Section Header */}
      <SectionHeader
        title={formatKey(schemaType.replace(/([A-Z])/g, ' $1').trim())}
        subtitle={`Analysis contains ${processedData.totalSections} data point${processedData.totalSections !== 1 ? 's' : ''}`}
        analysisType={analysisType}
        size="md"
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
        metadata={{
          ...metadata,
          totalSections: processedData.totalSections,
        }}
        quickActions={{
          showExport: Boolean(onExport),
          showShare: Boolean(onShare),
          onExport,
          onShare,
          customActions: [
            ...(onBookmark
              ? [
                  {
                    icon: Bookmark,
                    label: 'Bookmark',
                    onClick: onBookmark,
                  },
                ]
              : []),
            {
              icon: showFilters ? X : SlidersHorizontal,
              label: showFilters ? 'Hide Filters' : 'Show Filters',
              onClick: () => setShowFilters(!showFilters),
            },
          ],
        }}
      />

      {isExpanded && (
        <>
          {/* Summary Card */}
          <AnalysisSummaryCard
            title={formatKey(schemaType.replace(/([A-Z])/g, ' $1').trim())}
            summary={analysis.section_summary || analysis.executive_summary || analysis.description}
            insights={analysis.consolidated_insights || analysis.key_insights}
            metrics={{
              totalSections: processedData.totalSections,
              significantItems: processedData.significantItems,
              categories: processedData.categories,
            }}
          />

          {/* Content Categories Tab Navigation */}
          {processedData.totalSections > 5 && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <button
                  onClick={() => setActiveTab('all')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                    activeTab === 'all'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Layers className="h-3 w-3 inline mr-1" />
                  All ({processedData.totalSections})
                </button>

                {processedData.hasFinancialData && (
                  <button
                    onClick={() => setActiveTab('financial')}
                    className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                      activeTab === 'financial'
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <DollarSign className="h-3 w-3 inline mr-1" />
                    Financial ({processedData.categorizedContent.financial.length})
                  </button>
                )}

                {processedData.hasRiskData && (
                  <button
                    onClick={() => setActiveTab('risks')}
                    className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                      activeTab === 'risks'
                        ? 'bg-red-100 text-red-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <Shield className="h-3 w-3 inline mr-1" />
                    Risks ({processedData.categorizedContent.risks.length})
                  </button>
                )}

                {processedData.hasBusinessData && (
                  <button
                    onClick={() => setActiveTab('business')}
                    className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                      activeTab === 'business'
                        ? 'bg-teal-100 text-teal-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <Building className="h-3 w-3 inline mr-1" />
                    Business ({processedData.categorizedContent.business.length})
                  </button>
                )}

                {processedData.categorizedContent.other.length > 0 && (
                  <button
                    onClick={() => setActiveTab('other')}
                    className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
                      activeTab === 'other'
                        ? 'bg-gray-100 text-gray-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    Other ({processedData.categorizedContent.other.length})
                  </button>
                )}
              </div>

              {/* Search and Filters */}
              <div className="flex flex-col sm:flex-row gap-3">
                {/* Search */}
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search analysis content..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Filter Toggle */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center gap-2"
                >
                  <Filter className="h-4 w-4" />
                  Filters
                  {showFilters ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </Button>
              </div>

              {/* Advanced Filters */}
              {showFilters && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Show:</span>
                    {(['all', 'financial', 'risks', 'business', 'significant'] as FilterType[]).map(
                      (filter) => (
                        <button
                          key={filter}
                          onClick={() => setActiveFilter(filter)}
                          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                            activeFilter === filter
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {filter === 'significant' ? 'Key Items' : formatKey(filter)}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Content Display */}
          <div className="space-y-4">
            {filteredContent.length === 0 ? (
              <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                <Eye className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Content Found</h3>
                <p className="text-sm">
                  {searchTerm
                    ? 'No analysis content matches your search criteria.'
                    : 'No analysis data available for the selected filters.'}
                </p>
                {(searchTerm || activeFilter !== 'all') && (
                  <div className="mt-4 space-x-2">
                    {searchTerm && (
                      <Button variant="outline" size="sm" onClick={clearSearch}>
                        Clear Search
                      </Button>
                    )}
                    {activeFilter !== 'all' && (
                      <Button variant="outline" size="sm" onClick={showAll}>
                        Show All
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="grid gap-4">
                {filteredContent.map((item) => (
                  <ContentRenderer key={item.key} item={item} />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Debug info (development only) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="text-xs">
          <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
            Debug: Schema & Processing Info
          </summary>
          <div className="mt-2 p-3 bg-gray-100 rounded font-mono text-gray-600 text-xs space-y-1">
            <div>Schema: {schemaType}</div>
            <div>Analysis Type: {analysisType}</div>
            <div>Total Items: {processedData.totalSections}</div>
            <div>Active Tab: {activeTab}</div>
            <div>Active Filter: {activeFilter}</div>
            <div>Filtered Items: {filteredContent.length}</div>
            <div>Has Financial: {processedData.hasFinancialData.toString()}</div>
            <div>Has Risk Data: {processedData.hasRiskData.toString()}</div>
            <div>Has Business Data: {processedData.hasBusinessData.toString()}</div>
          </div>
        </details>
      )}
    </div>
  )
}
