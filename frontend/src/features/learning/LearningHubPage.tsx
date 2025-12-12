import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnalysisFilters } from '@/components/analysis/AnalysisFilters'
import type { AnalysisFiltersState } from '@/components/analysis/types'
import { useThemeTokens } from '@/components/ThemeProvider'
import {
  useAnalyses,
  useLearningModules,
  useLearningProgress,
  useQuizAttempts,
  type ModuleAnalysisOption,
  type QuizAttemptRecord,
} from '@/lib/hooks'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import type { AnalysisResponse } from '@/lib/types/analysis'
import { LearningProgressHero } from '@/features/dashboard/components/LearningProgressHero'
import { LearningModulesSection } from '@/features/learning/components/LearningModulesSection'
import { QuizAttemptsSection } from '@/features/learning/components/QuizAttemptsSection'

const DEFAULT_FILTERS: AnalysisFiltersState = {
  companyOrTicker: '',
  filingType: '',
  dateFrom: '',
  dateTo: '',
  segment: 'all',
}

const DATE_FORMAT = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

const TEMPLATE_LABELS: Record<string, string> = {
  comprehensive: 'Comprehensive',
  financial_focused: 'Financial focus',
  risk_focused: 'Risk focus',
  business_focused: 'MD&A focus',
}

function buildSearchQuery(filters: AnalysisFiltersState): string | null {
  const terms = [filters.companyOrTicker.trim(), filters.filingType.trim()].filter(Boolean)
  if (terms.length === 0) {
    return null
  }

  return terms.join(' ')
}

function toStartOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(0, 0, 0, 0)
  return parsed
}

function toEndOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(23, 59, 59, 999)
  return parsed
}

function isWithinFilingDateRange(
  filingDate: string | null | undefined,
  filters: AnalysisFiltersState
) {
  if (!filters.dateFrom && !filters.dateTo) {
    return true
  }

  if (!filingDate) {
    return false
  }

  const parsed = new Date(filingDate)
  if (Number.isNaN(parsed.getTime())) {
    return false
  }

  const start = toStartOfDay(filters.dateFrom)
  const end = toEndOfDay(filters.dateTo)

  if (start && parsed < start) {
    return false
  }

  if (end && parsed > end) {
    return false
  }

  return true
}

function formatDateLabel(input?: string | null) {
  if (!input) {
    return 'Date pending'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return DATE_FORMAT.format(parsed)
}

function describeAnalysis(analysis: AnalysisResponse): string {
  const summary = analysis.summary
  const company = summary.company.name ?? 'Unknown company'
  const ticker = summary.company.ticker
  const companyLabel = ticker ? `${company} (${ticker})` : company
  const filingType = summary.filing.type ?? 'N/A'
  const filingDate = summary.filing.date ?? analysis.created_at ?? null
  const templateRaw = summary.filing.analysis_template
  const templateKey = typeof templateRaw === 'string' ? templateRaw.toLowerCase() : null
  const templateLabel = templateKey ? (TEMPLATE_LABELS[templateKey] ?? templateRaw) : null

  return [companyLabel, filingType, formatDateLabel(filingDate), templateLabel]
    .filter(Boolean)
    .join(' · ')
}

function extractAttemptAnalysisId(attempt: QuizAttemptRecord): string | null {
  const metadata = attempt.metadata ?? {}
  const direct =
    (metadata as { analysis_id?: unknown }).analysis_id ??
    (metadata as { analysisId?: unknown }).analysisId ??
    (metadata as { analysisID?: unknown }).analysisID

  if (typeof direct === 'string' && direct.trim()) {
    return direct
  }

  const nested = (metadata as { analysis?: unknown }).analysis
  if (nested && typeof nested === 'object') {
    const nestedRecord = nested as Record<string, unknown>
    const nestedId =
      (nestedRecord as { analysis_id?: unknown }).analysis_id ??
      (nestedRecord as { analysisId?: unknown }).analysisId
    if (typeof nestedId === 'string' && nestedId.trim()) {
      return nestedId
    }
  }

  return null
}

function extractAttemptModuleKey(attempt: QuizAttemptRecord): string | null {
  const metadata = attempt.metadata ?? {}
  const direct =
    (metadata as { module_key?: unknown }).module_key ??
    (metadata as { moduleKey?: unknown }).moduleKey ??
    (metadata as { learning_module_key?: unknown }).learning_module_key ??
    (metadata as { quizId?: unknown }).quizId

  if (typeof direct === 'string' && direct.trim()) {
    return direct
  }

  return attempt.quizId ?? null
}

export function LearningHubPage() {
  const tokens = useThemeTokens()
  const [filters, setFilters] = useState<AnalysisFiltersState>(DEFAULT_FILTERS)
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null)

  const searchTerm = useMemo(() => buildSearchQuery(filters), [filters])

  const analysesQuery = useAnalyses(
    {
      status: 'COMPLETED',
      segment: 'all',
      sort: 'filing_date',
      direction: 'desc',
      page_size: 30,
      ...(searchTerm ? { search: searchTerm } : {}),
    },
    {
      staleTime: 5 * 60 * 1000,
      gcTime: 15 * 60 * 1000,
    }
  )

  const availableAnalyses = useMemo(() => {
    const items = analysesQuery.data?.items ?? []
    const search = filters.companyOrTicker.trim().toLowerCase()

    return items.filter((analysis) => {
      const summary = analysis.summary
      const filingType = summary.filing.type ?? ''
      const templateRaw = summary.filing.analysis_template
      const templateKey = typeof templateRaw === 'string' ? templateRaw.toLowerCase() : null
      const company = summary.company.name ?? ''
      const ticker = summary.company.ticker ?? ''
      const matchesForm = !filters.filingType || filingType === filters.filingType
      const matchesSegment = filters.segment === 'all' ? true : templateKey === filters.segment
      const matchesSearch =
        !search || company.toLowerCase().includes(search) || ticker.toLowerCase().includes(search)
      const matchesDate = isWithinFilingDateRange(summary.filing.date ?? null, filters)

      return matchesForm && matchesSegment && matchesSearch && matchesDate
    })
  }, [analysesQuery.data, filters])

  useEffect(() => {
    if (availableAnalyses.length === 0) {
      setSelectedAnalysisId(null)
      return
    }

    setSelectedAnalysisId((current) =>
      current && availableAnalyses.some((analysis) => analysis.analysis_id === current)
        ? current
        : availableAnalyses[0].analysis_id
    )
  }, [availableAnalyses])

  const selectedAnalysis = useMemo(
    () => availableAnalyses.find((analysis) => analysis.analysis_id === selectedAnalysisId) ?? null,
    [availableAnalyses, selectedAnalysisId]
  )

  const {
    data: learningModules = [],
    isLoading: modulesLoading,
    isError: modulesError,
    error: modulesErrorValue,
    refetch: refetchModules,
  } = useLearningModules({
    analysisIds: selectedAnalysisId ? [selectedAnalysisId] : [],
    enabled: Boolean(selectedAnalysisId),
    analysisLimit: selectedAnalysisId ? 1 : undefined,
  })

  const {
    progressByModule,
    dashboardHighlights,
    getSectionProgressSnapshot,
    isLoading: progressLoading,
    isRefetching: progressRefetching,
    updateProgress,
    error: progressError,
    clearError: clearProgressError,
  } = useLearningProgress({ modules: learningModules })

  const {
    attempts,
    isLoading: attemptsLoading,
    error: quizError,
    clearError: clearQuizError,
  } = useQuizAttempts({ limit: 100 })

  const moduleKeysForSelection = useMemo(
    () => new Set(learningModules.map((module) => module.moduleKey)),
    [learningModules]
  )

  const filteredAttempts = useMemo(() => {
    if (!selectedAnalysisId) {
      return []
    }

    return attempts.filter((attempt) => {
      const attemptAnalysisId = extractAttemptAnalysisId(attempt)
      if (attemptAnalysisId) {
        return attemptAnalysisId === selectedAnalysisId
      }

      const moduleKey = extractAttemptModuleKey(attempt)
      if (moduleKey && moduleKeysForSelection.has(moduleKey)) {
        return true
      }

      return false
    })
  }, [attempts, selectedAnalysisId, moduleKeysForSelection])

  const filteredAttemptStats = useMemo(() => {
    if (filteredAttempts.length === 0) {
      return { averageScore: null, passedCount: 0 }
    }

    const total = filteredAttempts.reduce((sum, attempt) => sum + attempt.scorePercent, 0)
    const passedCount = filteredAttempts.filter((attempt) => attempt.passed).length

    return {
      averageScore: total / filteredAttempts.length,
      passedCount,
    }
  }, [filteredAttempts])

  const unlockAttemptIds = useMemo(() => {
    const ids = new Set<string>()
    const attemptsByQuiz: Record<string, QuizAttemptRecord[]> = {}

    for (const attempt of filteredAttempts) {
      const moduleKey = extractAttemptModuleKey(attempt)
      if (!moduleKey) {
        continue
      }
      if (!attemptsByQuiz[moduleKey]) {
        attemptsByQuiz[moduleKey] = []
      }
      attemptsByQuiz[moduleKey].push(attempt)
    }

    for (const [moduleKey, progress] of Object.entries(progressByModule)) {
      if (!progress?.isUnlocked || !progress.unlockedAt) {
        continue
      }

      const attemptsForQuiz = attemptsByQuiz[moduleKey] ?? []
      const passing = attemptsForQuiz.filter((attempt) => attempt.scorePercent >= 80)
      if (passing.length === 0) {
        continue
      }

      const targetTimestamp = progress.unlockedAt
      let match = passing.find((attempt) => attempt.attemptedAt === targetTimestamp)

      if (!match) {
        const beforeOrAt = passing
          .filter((attempt) => attempt.attemptedAt <= targetTimestamp)
          .sort((a, b) => b.attemptedAt.localeCompare(a.attemptedAt))
        match = beforeOrAt[0]
      }

      if (!match) {
        match = passing.sort((a, b) => b.attemptedAt.localeCompare(a.attemptedAt))[0]
      }

      if (match) {
        ids.add(match.attemptId)
      }
    }

    return ids
  }, [filteredAttempts, progressByModule])

  const moduleErrorMessage =
    selectedAnalysisId && modulesError
      ? modulesErrorValue instanceof Error
        ? modulesErrorValue.message
        : 'Failed to load learning modules.'
      : null

  const analysisErrorMessage =
    analysesQuery.error instanceof Error
      ? analysesQuery.error.message
      : analysesQuery.error
        ? 'Unable to load analyses for these filters.'
        : null

  const navigate = useNavigate()

  const handleFiltersChange = (updates: Partial<AnalysisFiltersState>) =>
    setFilters((current) => ({ ...current, ...updates }))

  const handleAnalysisSelect = (analysisId: string) =>
    setSelectedAnalysisId(analysisId ? analysisId : null)

  const handleResumeModule = useCallback(
    async (module: LearningModule, option: ModuleAnalysisOption | null) => {
      const ctas = option?.ctas ?? module.ctas
      const walkthroughCta = ctas.find((cta) => cta.kind === 'walkthrough')
      if (!walkthroughCta) {
        return
      }

      const focusSectionState =
        walkthroughCta.focusSection ??
        walkthroughCta.sectionName ??
        option?.focusSection ??
        module.focusSection ??
        null

      const existing = progressByModule[module.moduleKey]
      const currentPercent = existing?.progressPercent ?? 0
      const metadata: Record<string, unknown> = { ...(existing?.metadata ?? {}) }
      const rawIntent = metadata['intended_next_sections']
      const intendedMap: Record<string, unknown> =
        rawIntent && typeof rawIntent === 'object' && rawIntent !== null
          ? { ...(rawIntent as Record<string, unknown>) }
          : {}

      const targetSectionKey = walkthroughCta.sectionKey ?? option?.sectionKey ?? module.sectionKey
      const timestamp = new Date().toISOString()
      const analysisIdentifier = option?.analysisId ?? walkthroughCta.analysisId

      intendedMap[analysisIdentifier] = {
        section_key: targetSectionKey,
        focus_section: focusSectionState,
        updated_at: timestamp,
      }

      metadata['intended_next_sections'] = intendedMap

      try {
        await updateProgress({
          moduleKey: module.moduleKey,
          progressPercent: currentPercent,
          metadata,
          progressId: existing?.progressId,
          lastInteractionAt: timestamp,
        })
      } catch {
        // Hook error state already captures and surfaces the failure.
      }

      navigate(`/filing/${analysisIdentifier}`, {
        state: {
          focusTab: walkthroughCta.focusTab,
          focusSection: focusSectionState,
        },
      })
    },
    [progressByModule, updateProgress, navigate]
  )

  const toastMessages = useMemo(
    () =>
      [
        progressError
          ? {
              id: 'progress-error',
              message: progressError,
              dismiss: clearProgressError,
            }
          : null,
        quizError
          ? {
              id: 'quiz-error',
              message: quizError,
              dismiss: clearQuizError,
            }
          : null,
      ].filter(Boolean) as Array<{ id: string; message: string; dismiss: () => void }>,
    [progressError, clearProgressError, quizError, clearQuizError]
  )

  return (
    <div className="relative min-h-screen w-full">
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full opacity-20 blur-[120px]"
          style={{ background: tokens.brand.accent }}
        />
        <div
          className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full opacity-15 blur-[100px]"
          style={{ background: tokens.action.primary }}
        />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl py-8 flex flex-col gap-8">
        {toastMessages.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="flex items-start justify-between gap-4 rounded-xl border px-4 py-3 text-sm backdrop-blur-sm"
            style={{
              borderColor: tokens.status.negative,
              background: 'rgba(231, 92, 74, 0.12)',
              color: tokens.status.negative,
            }}
          >
            <span>{toast.message}</span>
            <button
              type="button"
              onClick={toast.dismiss}
              className="text-xs font-semibold uppercase tracking-[0.18em]"
              style={{ color: tokens.status.negative }}
            >
              Dismiss
            </button>
          </div>
        ))}

        <LearningProgressHero
          highlights={dashboardHighlights}
          isLoading={progressLoading || progressRefetching}
        />

        <AnalysisFilters values={filters} onChange={handleFiltersChange} />

        <section
          className="flex flex-col gap-4 rounded-3xl border p-6 backdrop-blur-sm"
          style={{
            borderColor: 'var(--lines-subtle)',
            background: 'var(--surfaces-raised)',
            boxShadow: 'var(--shadows-soft)',
          }}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <span
                className="text-[11px] font-bold uppercase tracking-[0.2em]"
                style={{ color: 'var(--text-secondary)' }}
              >
                Analysis selection
              </span>
              <p
                className="text-sm"
                style={{
                  color: 'var(--text-muted)',
                  lineHeight: 'var(--typography-line-heights-standard)',
                }}
              >
                Choose a completed analysis to drive module sections and quiz attempts in the
                learning hub.
              </p>
            </div>
            {selectedAnalysis ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-primary)]">
                  {selectedAnalysis.summary.company.name ?? 'Unknown company'}
                </span>
                {selectedAnalysis.summary.company.ticker ? (
                  <span className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                    {selectedAnalysis.summary.company.ticker}
                  </span>
                ) : null}
                {selectedAnalysis.summary.filing.type ? (
                  <span className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]">
                    {selectedAnalysis.summary.filing.type}
                  </span>
                ) : null}
                <span className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]">
                  {formatDateLabel(
                    selectedAnalysis.summary.filing.date ?? selectedAnalysis.created_at ?? null
                  )}
                </span>
              </div>
            ) : null}
          </div>

          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
              <select
                value={selectedAnalysisId ?? ''}
                onChange={(event) => handleAnalysisSelect(event.target.value)}
                className="h-11 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
                style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
                disabled={analysesQuery.isLoading || availableAnalyses.length === 0}
              >
                {availableAnalyses.length === 0 ? (
                  <option value="">
                    {analysesQuery.isLoading ? 'Loading analyses...' : 'No matching analyses'}
                  </option>
                ) : null}
                {availableAnalyses.map((analysis) => (
                  <option key={analysis.analysis_id} value={analysis.analysis_id}>
                    {describeAnalysis(analysis)}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]">
              <span>
                {analysesQuery.isLoading
                  ? 'Loading analyses...'
                  : availableAnalyses.length === 0
                    ? 'No completed analyses match these filters.'
                    : `${availableAnalyses.length} matching analysis${availableAnalyses.length === 1 ? '' : 'es'}`}
              </span>
              {analysisErrorMessage ? (
                <span style={{ color: tokens.status.negative }}>{analysisErrorMessage}</span>
              ) : null}
            </div>
          </div>
        </section>

        {selectedAnalysisId ? (
          <LearningModulesSection
            modules={learningModules}
            isLoading={modulesLoading}
            moduleErrorMessage={moduleErrorMessage}
            tokens={tokens}
            onRetryModules={() => void refetchModules()}
            onResume={(module, option) => void handleResumeModule(module, option)}
            getSectionProgressSnapshot={getSectionProgressSnapshot}
          />
        ) : (
          <div
            className="rounded-3xl border px-6 py-8 text-sm backdrop-blur-sm"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            {analysesQuery.isLoading
              ? 'Loading analyses to populate your learning modules.'
              : availableAnalyses.length === 0
                ? 'No completed analyses match these filters. Adjust the filters or run a new analysis to unlock guided sections.'
                : 'Select an analysis above to load its guided walkthrough sections.'}
          </div>
        )}

        {selectedAnalysisId ? (
          <QuizAttemptsSection
            attempts={filteredAttempts}
            attemptsLoading={attemptsLoading}
            stats={filteredAttemptStats}
            tokens={tokens}
            unlockAttemptIds={unlockAttemptIds}
          />
        ) : (
          <div
            className="rounded-3xl border px-6 py-6 text-sm backdrop-blur-sm"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-raised)',
              color: 'var(--text-secondary)',
            }}
          >
            {analysesQuery.isLoading
              ? 'Loading quiz attempts...'
              : availableAnalyses.length === 0
                ? 'Run or select an analysis to see quiz attempts tied to that walkthrough.'
                : 'Select an analysis above to review quiz attempts for its guided sections.'}
          </div>
        )}
      </div>
    </div>
  )
}
