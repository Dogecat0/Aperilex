import { useState } from 'react'
import { ChevronDown, ChevronRight, FileText, TrendingUp } from 'lucide-react'
import type { AnalysisFullResults } from '@/api/types'

interface AnalysisViewerProps {
  results: AnalysisFullResults
}

export function AnalysisViewer({ results }: AnalysisViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  const toggleSection = (sectionName: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionName)) {
      newExpanded.delete(sectionName)
    } else {
      newExpanded.add(sectionName)
    }
    setExpandedSections(newExpanded)
  }

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive':
        return 'text-success-600 bg-success-50 border-success-200'
      case 'negative':
        return 'text-error-600 bg-error-50 border-error-200'
      case 'mixed':
        return 'text-warning-600 bg-warning-50 border-warning-200'
      case 'neutral':
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getSentimentLabel = (sentiment?: string) => {
    return sentiment ? sentiment.charAt(0).toUpperCase() + sentiment.slice(1) : 'Neutral'
  }

  if (!results.sections || results.sections.length === 0) {
    return (
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <div className="text-center py-8">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Section Results</h3>
          <p className="text-gray-500">
            This analysis doesn't contain detailed section-by-section results.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Overall Analysis Info */}
      {results.overall_sentiment && (
        <div className="bg-white rounded-lg border shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Overall Analysis</h2>
            <div
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getSentimentColor(results.overall_sentiment)}`}
            >
              <TrendingUp className="h-4 w-4 mr-1" />
              {getSentimentLabel(results.overall_sentiment)}
            </div>
          </div>

          {results.metadata && Object.keys(results.metadata).length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              {Object.entries(results.metadata).map(([key, value]) => (
                <div key={key} className="text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </div>
                  <div className="text-sm text-gray-600 capitalize">{key.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Section Results */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Section Analysis</h2>
          <p className="text-gray-600 text-sm mt-1">
            Detailed analysis of {results.sections.length} filing sections
          </p>
        </div>

        <div className="divide-y divide-gray-200">
          {results.sections.map((section, index) => {
            const isExpanded = expandedSections.has(section.section_name)

            return (
              <div key={section.section_name} className="p-6">
                <button
                  onClick={() => toggleSection(section.section_name)}
                  className="w-full flex items-center justify-between text-left hover:bg-gray-50 -m-2 p-2 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-primary-700 text-sm font-medium">
                      {index + 1}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{section.section_name}</h3>
                      {section.sentiment && (
                        <div className="flex items-center gap-2 mt-1">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSentimentColor(section.sentiment)}`}
                          >
                            {getSentimentLabel(section.sentiment)}
                          </span>
                          {section.confidence && (
                            <span className="text-xs text-gray-500">
                              {Math.round(section.confidence * 100)}% confidence
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="mt-4 ml-11 space-y-4">
                    {section.summary && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Summary</h4>
                        <p className="text-gray-700 leading-relaxed">{section.summary}</p>
                      </div>
                    )}

                    {section.key_points && section.key_points.length > 0 && (
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Key Points</h4>
                        <ul className="space-y-2">
                          {section.key_points.map((point, pointIndex) => (
                            <li key={pointIndex} className="flex gap-2">
                              <div className="w-1.5 h-1.5 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
                              <span className="text-gray-700">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
