import React from 'react'
import { FilingAnalysisSection } from '@/features/filings/components/FilingAnalysisSection'
import { useProgressiveFilingAnalysis, useFilingAnalysis } from '@/hooks/useFiling'

interface ProgressiveAnalysisExampleProps {
  accessionNumber: string
}

/**
 * Example component demonstrating how to use the progressive filing analysis
 * with enhanced loading states and user feedback.
 *
 * This component shows the pattern for implementing progressive loading
 * states in filing analysis workflows.
 */
export const ProgressiveAnalysisExample: React.FC<ProgressiveAnalysisExampleProps> = ({
  accessionNumber,
}) => {
  // Use the progressive analysis hook for enhanced UX
  const {
    analysisProgress,
    startAnalysis,
    resetProgress: _resetProgress,
    isAnalyzing,
  } = useProgressiveFilingAnalysis()

  // Also get existing analysis if available
  const {
    data: existingAnalysis,
    isLoading: isLoadingAnalysis,
    error: analysisError,
  } = useFilingAnalysis(accessionNumber)

  const handleStartAnalysis = async () => {
    try {
      await startAnalysis(accessionNumber, {
        analysis_type: 'COMPREHENSIVE',
        force_reanalysis: false,
      })
    } catch (error) {
      console.error('Analysis failed:', error)
      // Error state is already handled by the hook
    }
  }

  const handleViewFullAnalysis = () => {
    // Navigate to full analysis view
    console.log('Navigate to full analysis for:', accessionNumber)
  }

  return (
    <div className="space-y-4">
      <div className="border-b pb-4">
        <h2 className="text-xl font-semibold">Progressive Analysis Example</h2>
        <p className="text-sm text-muted-foreground mt-1">Accession Number: {accessionNumber}</p>
      </div>

      <FilingAnalysisSection
        analysis={existingAnalysis || null}
        isLoading={isLoadingAnalysis}
        error={analysisError}
        onAnalyze={handleStartAnalysis}
        onViewFullAnalysis={handleViewFullAnalysis}
        isAnalyzing={isAnalyzing}
        analysisProgress={analysisProgress}
      />

      {/* Debug Information */}
      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground">Debug Info</summary>
        <pre className="mt-2 p-2 bg-muted rounded text-xs">
          {JSON.stringify(
            {
              isAnalyzing,
              analysisProgress,
              hasExistingAnalysis: !!existingAnalysis,
              isLoadingAnalysis,
              hasError: !!analysisError,
            },
            null,
            2
          )}
        </pre>
      </details>
    </div>
  )
}

export default ProgressiveAnalysisExample
