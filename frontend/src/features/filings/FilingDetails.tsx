import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import {
  useFiling,
  useFilingAnalysis,
  useFilingAnalyzeMutation,
  usePollAnalysisCompletion,
} from '@/hooks/useFiling'
import { FilingMetadata } from './components/FilingMetadata'
import { FilingAnalysisSection } from './components/FilingAnalysisSection'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  Download,
  ExternalLink,
  RefreshCw,
  Play,
  Eye,
} from 'lucide-react'
import type { AnalyzeFilingRequest } from '@/api/types'

export function FilingDetails() {
  const { accessionNumber } = useParams<{ accessionNumber: string }>()
  const navigate = useNavigate()
  const { setBreadcrumbs } = useAppStore()
  const [isPolling, setIsPolling] = useState(false)

  const {
    data: filing,
    isLoading: filingLoading,
    error: filingError,
  } = useFiling(accessionNumber || '', {
    enabled: !!accessionNumber,
  })

  const {
    data: analysis,
    isLoading: analysisLoading,
    error: analysisError,
    refetch: refetchAnalysis,
  } = useFilingAnalysis(accessionNumber || '', {
    enabled: !!accessionNumber,
  })

  const analyzeFiling = useFilingAnalyzeMutation()
  const pollAnalysisCompletion = usePollAnalysisCompletion()

  // Set breadcrumbs when filing data loads
  React.useEffect(() => {
    if (filing && accessionNumber) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Filings', href: '/filings' },
        {
          label: `${filing.filing_type} - ${filing.accession_number}`,
          isActive: true,
        },
      ])
    } else if (accessionNumber) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Filings', href: '/filings' },
        { label: accessionNumber, isActive: true },
      ])
    }
  }, [filing, accessionNumber, setBreadcrumbs])

  const handleBack = () => {
    navigate('/filings')
  }

  const handleAnalyze = async (options?: AnalyzeFilingRequest) => {
    if (!accessionNumber) return

    try {
      setIsPolling(true)

      // Start the analysis
      await analyzeFiling.mutateAsync({
        accessionNumber,
        options: options || { analysis_type: 'COMPREHENSIVE' },
      })

      // Poll for completion
      await pollAnalysisCompletion.mutateAsync({
        accessionNumber,
        pollIntervalMs: 3000,
        maxAttempts: 40, // 2 minutes
      })

      // Refetch analysis data
      await refetchAnalysis()
    } catch (error) {
      console.error('Analysis failed:', error)
      // TODO: Show error toast
    } finally {
      setIsPolling(false)
    }
  }

  const handleViewFullAnalysis = () => {
    if (accessionNumber) {
      navigate(`/filings/${accessionNumber}/analysis`)
    }
  }

  const handleDownloadFiling = () => {
    // TODO: Implement filing download
    console.log('Download filing:', accessionNumber)
  }

  const handleViewOnSEC = () => {
    if (filing) {
      // Construct SEC EDGAR URL
      const secUrl = `https://www.sec.gov/Archives/edgar/data/${filing.company_id}/${filing.accession_number.replace(/-/g, '')}/${filing.accession_number}-index.htm`
      window.open(secUrl, '_blank')
    }
  }

  if (!accessionNumber) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <div>
            <h3 className="font-medium text-destructive">Invalid Filing</h3>
            <p className="text-sm text-muted-foreground mt-1">
              No accession number provided in the URL.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (filingError) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={handleBack} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Filings
        </Button>
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <div>
              <h3 className="font-medium text-destructive">Filing Not Found</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Could not find filing with accession number "{accessionNumber}".
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
        <Button variant="ghost" onClick={handleBack} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Filings
        </Button>
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

  const isAnalyzing = analyzeFiling.isPending || pollAnalysisCompletion.isPending || isPolling

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Button variant="ghost" onClick={handleBack} className="mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Filings
      </Button>

      {/* Filing Header */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">{filing.filing_type} Filing</h1>
            <p className="text-muted-foreground">
              {filing.accession_number} • Filed {new Date(filing.filing_date).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={handleDownloadFiling}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button variant="outline" size="sm" onClick={handleViewOnSEC}>
              <ExternalLink className="w-4 h-4 mr-2" />
              View on SEC
            </Button>
            {!analysis && (
              <Button size="sm" onClick={() => handleAnalyze()} disabled={isAnalyzing}>
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="w-4 h-4 mr-2" />
                    Analyze Filing
                  </>
                )}
              </Button>
            )}
            {analysis && (
              <Button variant="outline" size="sm" onClick={handleViewFullAnalysis}>
                <Eye className="w-4 h-4 mr-2" />
                Full Analysis
              </Button>
            )}
          </div>
        </div>

        {/* Processing Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 text-sm">
            <span className="text-muted-foreground">
              Status: <span className="font-medium">{filing.processing_status}</span>
            </span>
            {filing.analyses_count !== undefined && (
              <span className="text-muted-foreground">
                Analyses: <span className="font-medium">{filing.analyses_count}</span>
              </span>
            )}
          </div>
          {isAnalyzing && (
            <div className="flex items-center space-x-2 text-sm text-blue-600">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analysis in progress...</span>
            </div>
          )}
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
          />
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Filing Metadata */}
          <FilingMetadata filing={filing} />

          {/* Quick Actions */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
            <div className="space-y-2">
              {!analysis && (
                <Button
                  className="w-full justify-start"
                  onClick={() => handleAnalyze({ analysis_type: 'COMPREHENSIVE' })}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Brain className="w-4 h-4 mr-2" />
                      Comprehensive Analysis
                    </>
                  )}
                </Button>
              )}

              {!analysis && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => handleAnalyze({ analysis_type: 'FINANCIAL_FOCUSED' })}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Financial Analysis
                    </>
                  )}
                </Button>
              )}

              {analysis && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => handleAnalyze({ force_reanalysis: true })}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Re-analyzing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Re-analyze Filing
                    </>
                  )}
                </Button>
              )}

              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={handleDownloadFiling}
              >
                <Download className="w-4 h-4 mr-2" />
                Download Filing
              </Button>

              <Button variant="outline" className="w-full justify-start" onClick={handleViewOnSEC}>
                <ExternalLink className="w-4 h-4 mr-2" />
                View on SEC EDGAR
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
