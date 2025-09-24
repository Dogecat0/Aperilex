/**
 * Utility functions for analysis metrics calculations and formatting
 */

/**
 * Formats processing time in seconds to a human-readable string
 * @param seconds - Processing time in seconds
 * @returns Formatted time string (e.g., "30s", "2m 15s", "1h 30m")
 */
export function formatProcessingTime(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return 'N/A'

  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

/**
 * Gets the appropriate color classes for analysis type badges
 * @param type - Analysis type string
 * @returns CSS class string for text and background colors
 */
const ANALYSIS_TYPE_COLORS: Record<string, string> = {
  filing_analysis: 'text-primary-600 bg-primary-50',
  comprehensive: 'text-primary-600 bg-primary-50',
  custom_query: 'text-indigo-600 bg-indigo-50',
  comparison: 'text-amber-600 bg-amber-50',
  historical_trend: 'text-teal-600 bg-teal-50',
  // Backward-compatibility for legacy template names that may still appear in cached data
  financial_focused: 'text-success-600 bg-success-50',
  risk_focused: 'text-error-600 bg-error-50',
  business_focused: 'text-teal-600 bg-teal-50',
}

export function getAnalysisTypeColor(type: string): string {
  return ANALYSIS_TYPE_COLORS[type] || 'text-gray-600 bg-gray-50'
}

export function getAnalysisTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    filing_analysis: 'Filing Analysis',
    comprehensive: 'Comprehensive Analysis',
    custom_query: 'Custom Query',
    comparison: 'Comparison Analysis',
    historical_trend: 'Historical Trend',
    financial_focused: 'Financial Focused',
    risk_focused: 'Risk Focused',
    business_focused: 'Business Focused',
  }

  if (labels[type]) {
    return labels[type]
  }

  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

/**
 * Processing speed rating based on time taken
 */
export type ProcessingSpeedRating = {
  label: 'Fast' | 'Medium' | 'Slow'
  colorClass: string
  dotColorClass: string
}

/**
 * Gets processing speed rating based on processing time
 * @param processingTimeSeconds - Processing time in seconds
 * @returns Speed rating object with label and color classes
 */
export function getProcessingSpeedRating(
  processingTimeSeconds?: number | null
): ProcessingSpeedRating | null {
  if (!processingTimeSeconds || processingTimeSeconds <= 0) return null

  if (processingTimeSeconds < 30) {
    return {
      label: 'Fast',
      colorClass: 'text-success-600',
      dotColorClass: 'bg-success-500',
    }
  }

  if (processingTimeSeconds < 60) {
    return {
      label: 'Medium',
      colorClass: 'text-warning-600',
      dotColorClass: 'bg-warning-500',
    }
  }

  return {
    label: 'Slow',
    colorClass: 'text-error-600',
    dotColorClass: 'bg-error-500',
  }
}

/**
 * Coverage rating based on sections analyzed
 */
export type CoverageRating = {
  label: 'Comprehensive' | 'Moderate' | 'Limited'
  colorClass: string
  dotColorClass: string
}

/**
 * Gets coverage rating based on number of sections analyzed
 * @param sectionsAnalyzed - Number of sections analyzed
 * @returns Coverage rating object with label and color classes
 */
export function getCoverageRating(sectionsAnalyzed?: number | null): CoverageRating | null {
  if (!sectionsAnalyzed || sectionsAnalyzed <= 0) return null

  if (sectionsAnalyzed >= 5) {
    return {
      label: 'Comprehensive',
      colorClass: 'text-success-600',
      dotColorClass: 'bg-success-500',
    }
  }

  if (sectionsAnalyzed >= 3) {
    return {
      label: 'Moderate',
      colorClass: 'text-warning-600',
      dotColorClass: 'bg-warning-500',
    }
  }

  return {
    label: 'Limited',
    colorClass: 'text-error-600',
    dotColorClass: 'bg-error-500',
  }
}

/**
 * Quality rating based on confidence score
 */
export type QualityRating = {
  label: 'Excellent' | 'Good' | 'Fair'
  colorClass: string
  progressBarClass: string
}

/**
 * Gets quality rating based on confidence score
 * @param confidenceScore - Confidence score between 0 and 1
 * @returns Quality rating object with label and color classes
 */
export function getQualityRating(confidenceScore?: number | null): QualityRating | null {
  if (confidenceScore == null || confidenceScore < 0 || confidenceScore > 1) return null

  if (confidenceScore >= 0.8) {
    return {
      label: 'Excellent',
      colorClass: 'text-success-600',
      progressBarClass: 'bg-success-500',
    }
  }

  if (confidenceScore >= 0.6) {
    return {
      label: 'Good',
      colorClass: 'text-warning-600',
      progressBarClass: 'bg-warning-500',
    }
  }

  return {
    label: 'Fair',
    colorClass: 'text-error-600',
    progressBarClass: 'bg-error-500',
  }
}
