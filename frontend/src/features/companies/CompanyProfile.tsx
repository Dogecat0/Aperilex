import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { useCompany, useCompanyAnalyses } from '@/hooks/useCompany'
import { CompanyHeader } from './components/CompanyHeader'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { AlertCircle, BarChart3, Calendar, TrendingUp } from 'lucide-react'
import type { AnalysisResponse } from '@/api/types'

interface CompanyAnalysisCardProps {
  analysis: AnalysisResponse
  onViewAnalysis?: (analysisId: string) => void
}

const CompanyAnalysisCard = React.forwardRef<HTMLDivElement, CompanyAnalysisCardProps>(
  ({ analysis, onViewAnalysis }, ref) => {
    const handleViewAnalysis = () => {
      if (onViewAnalysis) {
        onViewAnalysis(analysis.analysis_id)
      }
    }

    const getTemplateDisplayName = (template: string | undefined) => {
      if (!template) return 'Unknown Analysis'

      const displayNames: Record<string, string> = {
        comprehensive: 'Comprehensive Analysis',
        filing_analysis: 'Filing Analysis',
        custom_query: 'Custom Query',
        comparison: 'Comparison Analysis',
        historical_trend: 'Historical Trend Analysis',
      }
      return (
        displayNames[template] ||
        template.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
      )
    }

    return (
      <div ref={ref} className="rounded-lg border bg-card p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              <span className="font-medium text-sm">
                {getTemplateDisplayName(
                  (analysis as any).analysis_type || analysis.analysis_template
                )}
              </span>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleViewAnalysis}>
            View Details
          </Button>
        </div>

        <div className="space-y-2">
          {analysis.executive_summary && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {analysis.executive_summary}
            </p>
          )}

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-1">
                <Calendar className="w-3 h-3" />
                <span>{new Date(analysis.created_at).toLocaleDateString()}</span>
              </span>
              {analysis.confidence_score && (
                <span className="flex items-center space-x-1">
                  <TrendingUp className="w-3 h-3" />
                  <span>{Math.round(analysis.confidence_score * 100)}% confidence</span>
                </span>
              )}
            </div>
            {analysis.llm_provider && (
              <span className="text-muted-foreground">{analysis.llm_provider}</span>
            )}
          </div>
        </div>

        {analysis.key_insights && analysis.key_insights.length > 0 && (
          <div className="pt-2 border-t">
            <div className="text-xs font-medium mb-1">Key Insights</div>
            <div className="space-y-1">
              {analysis.key_insights.slice(0, 2).map((insight, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <div className="w-1 h-1 bg-primary rounded-full mt-2 flex-shrink-0" />
                  <span className="text-xs text-muted-foreground line-clamp-1">{insight}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
)

CompanyAnalysisCard.displayName = 'CompanyAnalysisCard'

export function CompanyProfile() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()
  const { setBreadcrumbs } = useAppStore()

  const {
    data: company,
    isLoading: companyLoading,
    error: companyError,
  } = useCompany(ticker || '', {
    includeRecentAnalyses: true,
    enabled: !!ticker,
  })

  const {
    data: analyses,
    isLoading: analysesLoading,
    error: analysesError,
  } = useCompanyAnalyses(ticker || '', {
    page: 1,
    page_size: 10,
    enabled: !!ticker,
  })

  // Set breadcrumbs when company data loads
  React.useEffect(() => {
    if (company) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Companies', href: '/companies' },
        { label: company.display_name, isActive: true },
      ])
    } else if (ticker) {
      setBreadcrumbs([
        { label: 'Dashboard', href: '/' },
        { label: 'Companies', href: '/companies' },
        { label: ticker.toUpperCase(), isActive: true },
      ])
    }
  }, [company, ticker, setBreadcrumbs])

  const handleAnalyzeFilings = () => {
    navigate('/filings')
  }

  const handleViewAllAnalyses = () => {
    navigate('/analyses')
  }

  const handleViewAnalysis = (analysisId: string) => {
    navigate(`/analyses/${analysisId}`)
  }

  if (!ticker) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
        <div className="flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-destructive" />
          <div>
            <h3 className="font-medium text-destructive">Invalid Company</h3>
            <p className="text-sm text-muted-foreground mt-1">
              No ticker symbol provided in the URL.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (companyError) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <div>
              <h3 className="font-medium text-destructive">Company Not Found</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Could not find company with ticker "{ticker.toUpperCase()}".
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (companyLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-48 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (!company) {
    return null
  }

  const analysesArray = Array.isArray(analyses) ? analyses : analyses?.items || []

  return (
    <div className="space-y-6">
      {/* Company Header */}
      <CompanyHeader
        company={company}
        onAnalyzeFilings={handleAnalyzeFilings}
        onViewAnalyses={handleViewAllAnalyses}
      />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Analyses Section */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-lg border bg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Company Analyses</h2>
            </div>

            {analysesLoading && (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            )}

            {analysesError && (
              <div className="text-center py-8">
                <AlertCircle className="mx-auto w-8 h-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  Could not load analyses for this company.
                </p>
              </div>
            )}

            {!analysesLoading && !analysesError && analysesArray.length === 0 && (
              <div className="text-center py-8">
                <BarChart3 className="mx-auto w-8 h-8 text-muted-foreground mb-2" />
                <h3 className="text-sm font-medium mb-1">No analyses available</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Start by analyzing this company's SEC filings.
                </p>
                <Button onClick={handleAnalyzeFilings}>Analyze Filings</Button>
              </div>
            )}

            {!analysesLoading && !analysesError && analysesArray.length > 0 && (
              <div className="space-y-3">
                {analysesArray.slice(0, 5).map((analysis) => (
                  <CompanyAnalysisCard
                    key={analysis.analysis_id}
                    analysis={analysis}
                    onViewAnalysis={handleViewAnalysis}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Company Stats */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Company Overview</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Total Analyses</span>
                <span className="font-medium">{analysesArray.length}</span>
              </div>
              {company.recent_analyses && company.recent_analyses.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Latest Analysis</span>
                  <span className="font-medium">
                    {new Date(company.recent_analyses[0].created_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">CIK Number</span>
                <span className="font-medium font-mono text-xs">{company.cik}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
