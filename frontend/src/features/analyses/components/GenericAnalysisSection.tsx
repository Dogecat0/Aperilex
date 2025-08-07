import React, { useState, useMemo } from 'react'
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Hash,
  Type,
  List,
  FileText,
  ToggleLeft,
  ToggleRight,
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
} from 'lucide-react'
import { RiskFactorList } from './RiskFactorCard'
import { FinancialMetricsGrid } from './FinancialMetricsGrid'
import { EnhancedSectionHeader, getAnalysisType, extractSectionMetadata } from './EnhancedSectionHeader'
import { Button } from '@/components/ui/Button'

interface GenericAnalysisSectionProps {
  analysis: any
  schemaType: string
  loading?: boolean
  onExport?: () => void
  onShare?: () => void
  onBookmark?: () => void
  className?: string
}

// Content filtering and categorization types
type ContentCategory = 'financial' | 'risks' | 'business' | 'other'
type FilterType = 'all' | 'financial' | 'risks' | 'business' | 'significant'

interface ContentItem {
  key: string
  value: any
  category: ContentCategory
  isSignificant: boolean
  type: 'object' | 'array' | 'string' | 'number' | 'boolean'
}

interface ProcessedAnalysisData {
  categorizedContent: Record<ContentCategory, ContentItem[]>
  totalItems: number
  hasFinancialData: boolean
  hasRiskData: boolean
  hasBusinessData: boolean
}

export function GenericAnalysisSection({ 
  analysis, 
  schemaType, 
  loading = false, 
  onExport, 
  onShare, 
  onBookmark,
  className = '' 
}: GenericAnalysisSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [searchTerm, setSearchTerm] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [activeTab, setActiveTab] = useState<ContentCategory | 'all'>('all')
  const [showFilters, setShowFilters] = useState(false)

  // Helper functions (defined before useMemo)
  const shouldShowValue = (key: string, value: any): boolean => {
    if (!searchTerm) return true
    const searchLower = searchTerm.toLowerCase()
    const keyMatch = key.toLowerCase().includes(searchLower)
    const valueMatch = typeof value === 'string' && value.toLowerCase().includes(searchLower)
    return keyMatch || valueMatch
  }

  const toggleItem = (path: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedItems(newExpanded)
  }

  const formatKey = (key: string): string => {
    return key
      .replace(/([A-Z])/g, ' $1')
      .replace(/_/g, ' ')
      .trim()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  // Process and categorize analysis data
  const processedData = useMemo((): ProcessedAnalysisData => {
    if (!analysis || typeof analysis !== 'object') {
      return {
        categorizedContent: { financial: [], risks: [], business: [], other: [] },
        totalItems: 0,
        hasFinancialData: false,
        hasRiskData: false,
        hasBusinessData: false,
      }
    }

    const categorizedContent: Record<ContentCategory, ContentItem[]> = {
      financial: [],
      risks: [],
      business: [],
      other: [],
    }

    const categorizeContent = (key: string, _value: any): ContentCategory => {
      const keyLower = key.toLowerCase()
      
      // Financial indicators
      if (keyLower.includes('financial') || keyLower.includes('revenue') || 
          keyLower.includes('income') || keyLower.includes('profit') ||
          keyLower.includes('cash') || keyLower.includes('debt') ||
          keyLower.includes('assets') || keyLower.includes('metric') ||
          keyLower.includes('ratio') || keyLower.includes('margin') ||
          keyLower.includes('balance') || keyLower.includes('flow')) {
        return 'financial'
      }
      
      // Risk indicators
      if (keyLower.includes('risk') || keyLower.includes('threat') ||
          keyLower.includes('challenge') || keyLower.includes('uncertainty') ||
          keyLower.includes('concern') || keyLower.includes('volatility')) {
        return 'risks'
      }
      
      // Business indicators
      if (keyLower.includes('business') || keyLower.includes('operation') ||
          keyLower.includes('market') || keyLower.includes('strategy') ||
          keyLower.includes('competitive') || keyLower.includes('product') ||
          keyLower.includes('customer') || keyLower.includes('growth') ||
          keyLower.includes('industry')) {
        return 'business'
      }
      
      return 'other'
    }

    const isSignificantContent = (key: string, _value: any): boolean => {
      const keyLower = key.toLowerCase()
      return keyLower.includes('key') || keyLower.includes('significant') ||
             keyLower.includes('major') || keyLower.includes('critical') ||
             keyLower.includes('important') || keyLower.includes('highlight') ||
             keyLower.includes('summary') || keyLower.includes('executive')
    }

    const getValueType = (value: any): ContentItem['type'] => {
      if (Array.isArray(value)) return 'array'
      if (typeof value === 'object' && value !== null) return 'object'
      if (typeof value === 'boolean') return 'boolean'
      if (typeof value === 'number') return 'number'
      return 'string'
    }

    // Process analysis keys
    Object.keys(analysis).forEach(key => {
      if (shouldShowValue(key, analysis[key])) {
        const category = categorizeContent(key, analysis[key])
        const contentItem: ContentItem = {
          key,
          value: analysis[key],
          category,
          isSignificant: isSignificantContent(key, analysis[key]),
          type: getValueType(analysis[key])
        }
        categorizedContent[category].push(contentItem)
      }
    })

    return {
      categorizedContent,
      totalItems: Object.values(categorizedContent).reduce((sum, items) => sum + items.length, 0),
      hasFinancialData: categorizedContent.financial.length > 0,
      hasRiskData: categorizedContent.risks.length > 0,
      hasBusinessData: categorizedContent.business.length > 0,
    }
  }, [analysis, searchTerm])

  // Enhanced rendering for specialized content
  const renderSpecializedContent = (analysis: any): React.ReactNode | null => {
    // Financial metrics (single metric or array)
    if (analysis.metric_name && (analysis.current_value || analysis.previous_value)) {
      return (
        <FinancialMetricsGrid 
          metrics={[analysis]} 
          title="Financial Metrics"
          showComparisons={true}
          highlightSignificant={true}
          maxDisplayCount={6}
          loading={loading}
        />
      )
    }
    
    if (Array.isArray(analysis) && analysis.length > 0 && analysis[0].metric_name) {
      return (
        <FinancialMetricsGrid 
          metrics={analysis} 
          title="Financial Metrics"
          showComparisons={true}
          highlightSignificant={true}
          maxDisplayCount={6}
          loading={loading}
        />
      )
    }

    // Risk factors
    if (Array.isArray(analysis) && analysis.length > 0 && analysis[0].risk_name) {
      return <RiskFactorList risks={analysis} showHeader={false} />
    }

    // Key financial metrics from nested structures
    if (analysis.key_financial_metrics && Array.isArray(analysis.key_financial_metrics)) {
      return (
        <FinancialMetricsGrid 
          metrics={analysis.key_financial_metrics} 
          title="Key Financial Metrics"
          showComparisons={true}
          highlightSignificant={true}
          loading={loading}
        />
      )
    }

    // Risk factors from nested structures
    if (analysis.risk_factors && Array.isArray(analysis.risk_factors)) {
      return <RiskFactorList risks={analysis.risk_factors} showHeader={false} />
    }

    return null
  }

  // Get filtered content based on active filters
  const getFilteredContent = () => {
    const { categorizedContent } = processedData
    
    if (activeTab === 'all') {
      const allItems: ContentItem[] = []
      Object.values(categorizedContent).forEach(items => allItems.push(...items))
      return allItems.filter(item => {
        switch (activeFilter) {
          case 'financial':
            return item.category === 'financial'
          case 'risks':
            return item.category === 'risks'
          case 'business':
            return item.category === 'business'
          case 'significant':
            return item.isSignificant
          default:
            return true
        }
      })
    }
    
    return categorizedContent[activeTab].filter(item => {
      switch (activeFilter) {
        case 'significant':
          return item.isSignificant
        default:
          return true
      }
    })
  }

  const getValueIcon = (type: ContentItem['type']) => {
    switch (type) {
      case 'array': return List
      case 'object': return FileText
      case 'boolean': return ToggleLeft
      case 'number': return Hash
      default: return Type
    }
  }

  const renderValue = (value: any, path: string, level: number = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">Not provided</span>
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400 italic">No items</span>
      }

      // Special handling for risk factors
      if (value.length > 0 && value[0].risk_name) {
        return <RiskFactorList risks={value} showHeader={false} className="mt-2" />
      }

      const isExpanded = expandedItems.has(path)
      const hasComplexItems = value.some(item => typeof item === 'object' && item !== null)

      return (
        <div>
          <button
            onClick={() => toggleItem(path)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
          >
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <List className="h-4 w-4" />
            {value.length} item{value.length !== 1 ? 's' : ''}
          </button>

          {isExpanded && (
            <div className={`mt-3 ${level < 2 ? 'ml-4' : 'ml-2'} space-y-2`}>
              {value.map((item, index) => (
                <div
                  key={index}
                  className={`${
                    hasComplexItems
                      ? 'p-3 bg-gray-50 rounded-lg border border-gray-200'
                      : 'p-2 bg-gray-25 rounded text-sm'
                  } transition-colors hover:bg-gray-100`}
                >
                  {typeof item === 'object' && item !== null ? (
                    renderValue(item, `${path}[${index}]`, level + 1)
                  ) : (
                    <div className="text-gray-700">{String(item)}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'object' && value !== null) {
      const keys = Object.keys(value).filter(key => shouldShowValue(key, value[key]))
      
      if (keys.length === 0) {
        return <span className="text-gray-400 italic">No matching content</span>
      }

      const isExpanded = expandedItems.has(path)

      return (
        <div>
          <button
            onClick={() => toggleItem(path)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
          >
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <FileText className="h-4 w-4" />
            {keys.length} field{keys.length !== 1 ? 's' : ''}
          </button>

          {isExpanded && (
            <div className={`mt-3 ${level < 2 ? 'ml-4' : 'ml-2'} space-y-3`}>
              {keys.map(key => (
                <div key={key} className="border-l-3 border-blue-200 pl-4 hover:border-blue-300 transition-colors">
                  <div className="flex items-start gap-2">
                    <div className="font-medium text-sm text-gray-900 min-w-0 flex-1">
                      {formatKey(key)}
                    </div>
                  </div>
                  <div className="mt-2">
                    {renderValue(value[key], `${path}.${key}`, level + 1)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'boolean') {
      const Icon = value ? ToggleRight : ToggleLeft
      return (
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${value ? 'text-emerald-600' : 'text-gray-400'}`} />
          <span className={`font-medium ${value ? 'text-emerald-700' : 'text-gray-500'}`}>
            {value ? 'Yes' : 'No'}
          </span>
        </div>
      )
    }

    if (typeof value === 'number') {
      return (
        <div className="flex items-center gap-2">
          <Hash className="h-4 w-4 text-blue-500" />
          <span className="text-gray-700 font-mono font-medium">{value.toLocaleString()}</span>
        </div>
      )
    }

    // String values
    const stringValue = String(value)
    if (stringValue.length > 300) {
      const isExpanded = expandedItems.has(`${path}_text`)
      return (
        <div className="text-sm">
          <div className="text-gray-700 leading-relaxed">
            {isExpanded ? stringValue : `${stringValue.substring(0, 300)}...`}
          </div>
          <button
            onClick={() => toggleItem(`${path}_text`)}
            className="text-primary-600 hover:text-primary-700 text-sm mt-2 font-medium inline-flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" />
                Show more
              </>
            )}
          </button>
        </div>
      )
    }

    return <span className="text-gray-700 leading-relaxed text-sm">{stringValue}</span>
  }

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
      <div className={`flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
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

  // Check for specialized content first
  const specializedContent = renderSpecializedContent(analysis)
  const analysisType = getAnalysisType(schemaType)
  const metadata = extractSectionMetadata(analysis)
  const filteredContent = getFilteredContent()

  // Render specialized content if available
  if (specializedContent) {
    return (
      <div className={`space-y-6 ${className}`}>
        {/* Enhanced Section Header */}
        <EnhancedSectionHeader
          title={formatKey(schemaType.replace(/([A-Z])/g, ' $1').trim())}
          subtitle="Specialized analysis view with enhanced visualizations"
          analysisType={analysisType}
          size="md"
          isExpanded={isExpanded}
          onToggle={() => setIsExpanded(!isExpanded)}
          metadata={{
            ...metadata,
            totalItems: processedData.totalItems,
          }}
          quickActions={{
            showExport: Boolean(onExport),
            showShare: Boolean(onShare),
            onExport,
            onShare,
            customActions: onBookmark ? [{
              icon: Bookmark,
              label: 'Bookmark',
              onClick: onBookmark,
            }] : undefined,
          }}
        />

        {/* Specialized content */}
        {isExpanded && (
          <div className="space-y-4">
            {specializedContent}
          </div>
        )}

        {/* Debug info (development only) */}
        {process.env.NODE_ENV === 'development' && (
          <details className="text-xs">
            <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
              Debug: Schema & Processing Info
            </summary>
            <div className="mt-2 p-3 bg-gray-100 rounded font-mono text-gray-600 text-xs">
              <div>Schema: {schemaType}</div>
              <div>Analysis Type: {analysisType}</div>
              <div>Total Items: {processedData.totalItems}</div>
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
      <EnhancedSectionHeader
        title={formatKey(schemaType.replace(/([A-Z])/g, ' $1').trim())}
        subtitle={`Analysis contains ${processedData.totalItems} data point${processedData.totalItems !== 1 ? 's' : ''}`}
        analysisType={analysisType}
        size="md"
        isExpanded={isExpanded}
        onToggle={() => setIsExpanded(!isExpanded)}
        metadata={{
          ...metadata,
          totalItems: processedData.totalItems,
        }}
        quickActions={{
          showExport: Boolean(onExport),
          showShare: Boolean(onShare),
          onExport,
          onShare,
          customActions: [
            ...(onBookmark ? [{
              icon: Bookmark,
              label: 'Bookmark',
              onClick: onBookmark,
            }] : []),
            {
              icon: showFilters ? X : SlidersHorizontal,
              label: showFilters ? 'Hide Filters' : 'Show Filters',
              onClick: () => setShowFilters(!showFilters),
            }
          ],
        }}
      />

      {isExpanded && (
        <>
          {/* Content Categories Tab Navigation */}
          {processedData.totalItems > 5 && (
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
                  All ({processedData.totalItems})
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
                    <FileText className="h-3 w-3 inline mr-1" />
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
                  {showFilters ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </Button>
              </div>

              {/* Advanced Filters */}
              {showFilters && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Show:</span>
                    {(['all', 'financial', 'risks', 'business', 'significant'] as FilterType[]).map(filter => (
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
                    ))}
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
                      <Button variant="outline" size="sm" onClick={() => setSearchTerm('')}>
                        Clear Search
                      </Button>
                    )}
                    {activeFilter !== 'all' && (
                      <Button variant="outline" size="sm" onClick={() => setActiveFilter('all')}>
                        Show All
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ) : (
              filteredContent.map(item => {
                const ValueIcon = getValueIcon(item.type)
                return (
                  <div 
                    key={item.key} 
                    className={`bg-white border rounded-lg p-4 transition-all hover:shadow-md ${
                      item.isSignificant 
                        ? 'border-blue-200 bg-blue-50/30' 
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${
                        item.category === 'financial' ? 'bg-blue-100' :
                        item.category === 'risks' ? 'bg-red-100' :
                        item.category === 'business' ? 'bg-teal-100' :
                        'bg-gray-100'
                      }`}>
                        <ValueIcon className={`h-4 w-4 ${
                          item.category === 'financial' ? 'text-blue-600' :
                          item.category === 'risks' ? 'text-red-600' :
                          item.category === 'business' ? 'text-teal-600' :
                          'text-gray-600'
                        }`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h6 className="font-semibold text-gray-900">
                            {formatKey(item.key)}
                          </h6>
                          {item.isSignificant && (
                            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
                              Key
                            </span>
                          )}
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                            item.category === 'financial' ? 'bg-blue-100 text-blue-700' :
                            item.category === 'risks' ? 'bg-red-100 text-red-700' :
                            item.category === 'business' ? 'bg-teal-100 text-teal-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {formatKey(item.category)}
                          </span>
                        </div>
                        <div>
                          {renderValue(item.value, item.key)}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })
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
            <div>Total Items: {processedData.totalItems}</div>
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