import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { useFiling, useFilingAnalysis, useProgressiveFilingAnalysis } from '@/hooks/useFiling'
import { FilingMetadata } from './components/FilingMetadata'
import { FilingAnalysisSection } from './components/FilingAnalysisSection'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { AlertCircle, ExternalLink } from 'lucide-react'
import type { AnalyzeFilingRequest } from '@/api/types'

export function FilingDetails() {
  const { filingId } = useParams<{ filingId: string }>()
  const navigate = useNavigate()
  const { setBreadcrumbs } = useAppStore()

  const {
    data: filing,
    isLoading: filingLoading,
    error: filingError,
  } = useFiling(filingId || '', {
    enabled: !!filingId,
  })

  const {
    data: analysis,
    isLoading: analysisLoading,
    error: analysisError,
    refetch: refetchAnalysis,
  } = useFilingAnalysis(filingId || '', {
    enabled: !!filingId,
  })

  const {
    analysisProgress,
    startAnalysis,
    isAnalyzing,
    checkBackgroundAnalysis,
    isBackgroundProcessing,
  } = useProgressiveFilingAnalysis()

  // Set breadcrumbs when filing data loads
  React.useEffect(() => {
    if (filing && filingId) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Filings', href: '/filings' },
        {
          label: `${filing.filing_type} - ${filing.accession_number}`,
          isActive: true,
        },
      ])
    } else if (filingId) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Filings', href: '/filings' },
        { label: filingId, isActive: true },
      ])
    }
  }, [filing, filingId, setBreadcrumbs])

  // Auto-refetch analysis when it completes
  React.useEffect(() => {
    if (analysisProgress.state === 'completed') {
      refetchAnalysis()
    }
  }, [analysisProgress.state, refetchAnalysis])

  const handleAnalyze = async (options?: AnalyzeFilingRequest) => {
    if (!filingId) return

    try {
      // Use the progressive analysis system which handles progress tracking automatically
      const result = await startAnalysis(filingId, options)

      // If analysis completed successfully, refetch the analysis data
      if (result) {
        refetchAnalysis()
      }
    } catch (error) {
      console.error('Analysis failed:', error)
      // Error state is already handled by the progressive analysis hook
    }
  }

  const handleViewFullAnalysis = () => {
    if (filingId) {
      navigate(`/filings/${filingId}/analysis`)
    }
  }

  const handleViewOnSEC = () => {
    if (filing) {
      // Construct SEC EDGAR URL
      const secUrl = `https://www.sec.gov/Archives/edgar/data/${filing.company_id}/${filing.accession_number.replace(/-/g, '')}/${filing.accession_number}-index.htm`
      window.open(secUrl, '_blank')
    }
  }

  if (!filingId) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <div>
            <h3 className="font-medium text-destructive">Invalid Filing</h3>
            <p className="text-sm text-muted-foreground mt-1">
              No filing ID provided in the URL.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (filingError) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <div>
              <h3 className="font-medium text-destructive">Filing Not Found</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Could not find filing with ID "{filingId}".
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (filingLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (!filing) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Filing Header */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{filing.filing_type} Filing</h1>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={handleViewOnSEC}>
              <ExternalLink className="w-4 h-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">View on SEC</span>
              <span className="sm:hidden">SEC</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Analysis Section */}
        <div className="lg:col-span-2">
          <FilingAnalysisSection
            analysis={analysis || null}
            isLoading={analysisLoading}
            error={analysisError}
            onAnalyze={() => handleAnalyze()}
            onViewFullAnalysis={handleViewFullAnalysis}
            isAnalyzing={isAnalyzing}
            analysisProgress={analysisProgress}
            filingStatus={filing.processing_status}
            onCheckBackgroundAnalysis={checkBackgroundAnalysis}
            isBackgroundProcessing={isBackgroundProcessing}
          />
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Filing Metadata */}
          <FilingMetadata filing={filing} />
        </div>
      </div>
    </div>
  )
}
