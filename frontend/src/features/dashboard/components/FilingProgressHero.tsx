import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'

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
  readySectionCount: number
  latestAnalysis: LatestAnalysisHighlight | null
}

export function FilingProgressHero({
  isLoading,
  dateRangeLabel,
  totalCompleted,
  readySectionCount,
  latestAnalysis,
}: FilingProgressHeroProps) {
  const navigate = useNavigate()

  const heroCopy = useMemo(() => {
    const completionValue = isLoading ? '—' : `${totalCompleted}`
    const completionHelper =
      dateRangeLabel.toLowerCase() === 'all time'
        ? 'Across all completed analyses'
        : `Past ${dateRangeLabel}`

    const sectionsValue = isLoading ? '—' : `${readySectionCount}`
    const sectionsHelper =
      readySectionCount === 1 ? 'Guided section completed' : 'Guided sections completed'

    const latestValue = isLoading ? 'Loading…' : (latestAnalysis?.companyName ?? 'No filings yet')
    const latestHelper = latestAnalysis
      ? `${latestAnalysis.filingType ?? 'Filing'} · ${latestAnalysis.analyzedAt}`
      : 'Run an analysis to populate this slot.'

    return {
      completionValue,
      completionHelper,
      sectionsValue,
      sectionsHelper,
      latestValue,
      latestHelper,
    }
  }, [dateRangeLabel, isLoading, latestAnalysis, readySectionCount, totalCompleted])

  const handleResumeLatest = () => {
    if (!latestAnalysis) {
      return
    }
    navigate(`/filing/${latestAnalysis.analysisId}`)
  }

  const handleOpenAnalyze = () => {
    navigate('/analyze')
  }

  const hasLatestAnalysis = Boolean(latestAnalysis)

  return (
    <FeatureHero
      overline="Dashboard"
      title="Stay on top of your filings"
      description="Review recent walkthroughs, monitor sections you have covered, and jump straight back into the filing workspace."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <FeatureHeroStat
          label="Completed analyses"
          value={heroCopy.completionValue}
          helper={heroCopy.completionHelper}
        />
        <FeatureHeroStat
          label="Guided sections covered"
          value={heroCopy.sectionsValue}
          helper={heroCopy.sectionsHelper}
        />
        <FeatureHeroStat
          label="Latest completion"
          value={heroCopy.latestValue}
          helper={heroCopy.latestHelper}
        />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button type="button" size="sm" variant="primary" onClick={handleOpenAnalyze}>
          Run a new analysis
        </Button>
        {hasLatestAnalysis ? (
          <Button type="button" size="sm" variant="secondary" onClick={handleResumeLatest}>
            Resume latest walkthrough
          </Button>
        ) : null}
      </div>
    </FeatureHero>
  )
}
