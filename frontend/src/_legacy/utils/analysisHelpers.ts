// Content filtering and categorization types
export type ContentCategory = 'financial' | 'risks' | 'business' | 'other'
export type FilterType = 'all' | 'financial' | 'risks' | 'business' | 'significant'

export interface ContentItem {
  key: string
  value: any
  category: ContentCategory
  isSignificant: boolean
  type: 'object' | 'array' | 'string' | 'number' | 'boolean'
}

export interface ProcessedAnalysisData {
  categorizedContent: Record<ContentCategory, ContentItem[]>
  totalSections: number
  hasFinancialData: boolean
  hasRiskData: boolean
  hasBusinessData: boolean
  significantItems: number
  categories: Record<string, number>
}

/**
 * Format a camelCase or snake_case key to a readable title
 */
export function formatKey(key: string): string {
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Categorize content based on key name
 */
export function categorizeContent(key: string, _value: any): ContentCategory {
  const keyLower = key.toLowerCase()

  // Financial indicators
  if (
    keyLower.includes('financial') ||
    keyLower.includes('revenue') ||
    keyLower.includes('income') ||
    keyLower.includes('profit') ||
    keyLower.includes('cash') ||
    keyLower.includes('debt') ||
    keyLower.includes('assets') ||
    keyLower.includes('metric') ||
    keyLower.includes('ratio') ||
    keyLower.includes('margin') ||
    keyLower.includes('balance') ||
    keyLower.includes('flow')
  ) {
    return 'financial'
  }

  // Risk indicators
  if (
    keyLower.includes('risk') ||
    keyLower.includes('threat') ||
    keyLower.includes('challenge') ||
    keyLower.includes('uncertainty') ||
    keyLower.includes('concern') ||
    keyLower.includes('volatility')
  ) {
    return 'risks'
  }

  // Business indicators
  if (
    keyLower.includes('business') ||
    keyLower.includes('operation') ||
    keyLower.includes('market') ||
    keyLower.includes('strategy') ||
    keyLower.includes('competitive') ||
    keyLower.includes('product') ||
    keyLower.includes('customer') ||
    keyLower.includes('growth') ||
    keyLower.includes('industry')
  ) {
    return 'business'
  }

  return 'other'
}

/**
 * Determine if content is significant based on key name
 */
export function isSignificantContent(key: string, _value: any): boolean {
  const keyLower = key.toLowerCase()
  return (
    keyLower.includes('key') ||
    keyLower.includes('significant') ||
    keyLower.includes('major') ||
    keyLower.includes('critical') ||
    keyLower.includes('important') ||
    keyLower.includes('highlight') ||
    keyLower.includes('summary') ||
    keyLower.includes('executive')
  )
}

/**
 * Get the type of a value
 */
export function getValueType(value: any): ContentItem['type'] {
  if (Array.isArray(value)) return 'array'
  if (typeof value === 'object' && value !== null) return 'object'
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') return 'number'
  return 'string'
}

/**
 * Check if a value should be shown based on search term
 */
export function shouldShowValue(key: string, value: any, searchTerm: string): boolean {
  if (!searchTerm) return true
  const searchLower = searchTerm.toLowerCase()
  const keyMatch = key.toLowerCase().includes(searchLower)
  const valueMatch = typeof value === 'string' && value.toLowerCase().includes(searchLower)
  return keyMatch || valueMatch
}

/**
 * Process analysis data into categorized structure
 */
export function processAnalysisData(analysis: any, searchTerm: string = ''): ProcessedAnalysisData {
  if (!analysis || typeof analysis !== 'object') {
    return {
      categorizedContent: { financial: [], risks: [], business: [], other: [] },
      totalSections: 0,
      hasFinancialData: false,
      hasRiskData: false,
      hasBusinessData: false,
      significantItems: 0,
      categories: {},
    }
  }

  const categorizedContent: Record<ContentCategory, ContentItem[]> = {
    financial: [],
    risks: [],
    business: [],
    other: [],
  }

  let significantItems = 0

  // Process analysis keys
  Object.keys(analysis).forEach((key) => {
    if (shouldShowValue(key, analysis[key], searchTerm)) {
      const category = categorizeContent(key, analysis[key])
      const isSignificant = isSignificantContent(key, analysis[key])

      if (isSignificant) {
        significantItems++
      }

      const contentItem: ContentItem = {
        key,
        value: analysis[key],
        category,
        isSignificant,
        type: getValueType(analysis[key]),
      }
      categorizedContent[category].push(contentItem)
    }
  })

  // Create categories count map
  const categories: Record<string, number> = {}
  Object.entries(categorizedContent).forEach(([category, items]) => {
    if (items.length > 0) {
      categories[category] = items.length
    }
  })

  return {
    categorizedContent,
    totalSections: Object.values(categorizedContent).reduce((sum, items) => sum + items.length, 0),
    hasFinancialData: categorizedContent.financial.length > 0,
    hasRiskData: categorizedContent.risks.length > 0,
    hasBusinessData: categorizedContent.business.length > 0,
    significantItems,
    categories,
  }
}

/**
 * Filter content items based on active filters
 */
export function getFilteredContent(
  processedData: ProcessedAnalysisData,
  activeTab: ContentCategory | 'all',
  activeFilter: FilterType
): ContentItem[] {
  const { categorizedContent } = processedData

  if (activeTab === 'all') {
    const allItems: ContentItem[] = []
    Object.values(categorizedContent).forEach((items) => allItems.push(...items))
    return allItems.filter((item) => {
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

  return categorizedContent[activeTab].filter((item) => {
    switch (activeFilter) {
      case 'significant':
        return item.isSignificant
      default:
        return true
    }
  })
}

/**
 * Check if analysis data has specialized content that should use specialized renderers
 */
export function hasSpecializedContent(analysis: any): boolean {
  if (!analysis || typeof analysis !== 'object') return false

  // Check for financial metrics
  if (analysis.metric_name && (analysis.current_value || analysis.previous_value)) {
    return true
  }

  if (Array.isArray(analysis) && analysis.length > 0 && analysis[0].metric_name) {
    return true
  }

  // Check for risk factors
  if (Array.isArray(analysis) && analysis.length > 0 && analysis[0].risk_name) {
    return true
  }

  // Check for nested financial metrics
  if (analysis.key_financial_metrics && Array.isArray(analysis.key_financial_metrics)) {
    return true
  }

  // Check for nested risk factors
  if (analysis.risk_factors && Array.isArray(analysis.risk_factors)) {
    return true
  }

  return false
}

/**
 * Get category color classes
 */
export function getCategoryColors(category: ContentCategory) {
  switch (category) {
    case 'financial':
      return {
        icon: 'bg-blue-100 text-blue-600',
        badge: 'bg-blue-100 text-blue-700',
        border: 'border-blue-200',
      }
    case 'risks':
      return {
        icon: 'bg-red-100 text-red-600',
        badge: 'bg-red-100 text-red-700',
        border: 'border-red-200',
      }
    case 'business':
      return {
        icon: 'bg-teal-100 text-teal-600',
        badge: 'bg-teal-100 text-teal-700',
        border: 'border-teal-200',
      }
    default:
      return {
        icon: 'bg-gray-100 text-gray-600',
        badge: 'bg-gray-100 text-gray-700',
        border: 'border-gray-200',
      }
  }
}
