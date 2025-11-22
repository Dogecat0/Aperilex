import { useMemo } from 'react'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'

interface LatestAnalysisHighlight {
  analysisId: string
  companyName: string
  filingType?: string | null
  analyzedAt: string
}

interface FilingProgressHeroProps {
  isLoading: boolean
  dateRangeLabel: string
  totalCompleted: number
  analyzedCompanyCount: number
  latestAnalysis: LatestAnalysisHighlight | null
}

export function FilingProgressHero({
  isLoading,
  dateRangeLabel,
  totalCompleted,
  analyzedCompanyCount,
  latestAnalysis,
}: FilingProgressHeroProps) {
  const heroCopy = useMemo(() => {
    const completionValue = isLoading ? '—' : `${totalCompleted}`
    const completionHelper =
      dateRangeLabel.toLowerCase() === 'all time'
        ? 'Across all completed analyses'
        : `Past ${dateRangeLabel}`

    const companiesValue = isLoading ? '—' : `${analyzedCompanyCount}`
    const companiesHelper =
      analyzedCompanyCount === 1 ? 'Unique company in this view' : 'Unique companies in this view'

    const latestValue = isLoading ? 'Loading…' : (latestAnalysis?.companyName ?? 'No filings yet')
    const latestHelper = latestAnalysis
      ? `${latestAnalysis.filingType ?? 'Filing'} · ${latestAnalysis.analyzedAt}`
      : 'Run an analysis to populate this slot.'

    return {
      completionValue,
      completionHelper,
      companiesValue,
      companiesHelper,
      latestValue,
      latestHelper,
    }
  }, [analyzedCompanyCount, dateRangeLabel, isLoading, latestAnalysis, totalCompleted])

  return (
    <FeatureHero
      overline="Dashboard"
      title="Stay on top of your filings"
      description="Review recent walkthroughs, track companies you have analyzed, and jump straight back into the filing workspace."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <FeatureHeroStat
          label="Completed analyses"
          value={heroCopy.completionValue}
          helper={heroCopy.completionHelper}
        />
        <FeatureHeroStat
          label="Companies analyzed"
          value={heroCopy.companiesValue}
          helper={heroCopy.companiesHelper}
        />
        <FeatureHeroStat
          label="Latest completion"
          value={heroCopy.latestValue}
          helper={heroCopy.latestHelper}
        />
      </div>
    </FeatureHero>
  )
}
