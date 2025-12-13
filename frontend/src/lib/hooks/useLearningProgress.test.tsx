import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import { learningProgressResponses } from '@/../tests/fixtures/learning'
import type { LearningModule } from '@/lib/hooks'
import { useLearningProgress } from './useLearningProgress'

const getSpy = vi.spyOn(apiClient, 'get')
const putSpy = vi.spyOn(apiClient, 'put')
const postSpy = vi.spyOn(apiClient, 'post')

const sampleModules: LearningModule[] = [
  {
    key: 'mda_foundations::item-7',
    moduleKey: 'mda_foundations',
    sectionKey: 'Item 7 - Management Discussion & Analysis',
    title: 'Decode MD&A narratives',
    duration: '9 min walkthrough',
    summary:
      'Connect commentary to margin movements by practicing with the latest MD&A guided review.',
    focusTab: 'sections',
  },
  {
    key: 'risk_mastery::item-1a',
    moduleKey: 'risk_mastery',
    sectionKey: 'Item 1A - Risk Factors',
    title: 'Spot meaningful risk updates',
    duration: '7 min walkthrough',
    summary:
      'Track new and elevated risk disclosures by comparing recent filings once analyses complete.',
    focusTab: 'sections',
  },
]

function ProgressProbe() {
  const { progress, updateProgress, recordWalkthroughEvent, error, clearError } =
    useLearningProgress()
  const record = progress.find((item) => item.moduleKey === 'mda_foundations')

  return (
    <div>
      <div data-testid="progress-value">{record?.progressPercent ?? '0'}</div>
      {error && (
        <div role="alert">
          {error}
          <button onClick={clearError}>dismiss</button>
        </div>
      )}
      <button
        type="button"
        onClick={() =>
          void updateProgress({
            moduleKey: 'mda_foundations',
            progressPercent: 80,
            metadata: record?.metadata ?? {},
            progressId: record?.progressId,
          }).catch(() => {})
        }
      >
        mutate
      </button>
      <button
        type="button"
        onClick={() =>
          void recordWalkthroughEvent({
            analysisId: '11111111-1111-1111-1111-111111111111',
            moduleKey: 'mda_foundations',
            sectionKey: 'item-7',
            progressPercent: 100,
            completedAt: '2025-01-06T10:15:00Z',
          }).catch(() => {})
        }
      >
        walkthrough
      </button>
    </div>
  )
}

function HighlightsProbe() {
  const { dashboardHighlights } = useLearningProgress({ modules: sampleModules })

  return (
    <div>
      <div data-testid="completion-total">{dashboardHighlights.completion.total}</div>
      <div data-testid="sections-in-progress">{dashboardHighlights.sectionSummary.inProgress}</div>
      <div data-testid="next-lesson">
        {dashboardHighlights.nextLesson
          ? `${dashboardHighlights.nextLesson.moduleKey}::${dashboardHighlights.nextLesson.sectionKey}`
          : 'none'}
      </div>
    </div>
  )
}

function SnapshotProbe({ analysisId }: { analysisId?: string }) {
  const { getSectionProgressSnapshot } = useLearningProgress()
  const snapshot = getSectionProgressSnapshot(
    'mda_foundations',
    'Item 7 - Management Discussion & Analysis',
    analysisId ?? null
  )

  return (
    <div>
      <div data-testid="snapshot-percent">{snapshot.progressPercent}</div>
      <div data-testid="snapshot-status">{snapshot.status}</div>
    </div>
  )
}

describe('useLearningProgress', () => {
  beforeEach(() => {
    getSpy.mockReset()
    putSpy.mockReset()
    postSpy.mockReset()
    getSpy.mockResolvedValue(learningProgressResponses)
    putSpy.mockResolvedValue(learningProgressResponses[0])
    postSpy.mockResolvedValue(learningProgressResponses[0])
  })

  afterEach(() => {
    getSpy.mockReset()
    putSpy.mockReset()
    postSpy.mockReset()
  })

  it('fetches and normalizes progress records', async () => {
    renderWithProviders(<ProgressProbe />)

    await waitFor(() => expect(getSpy).toHaveBeenCalled())
    expect(getSpy).toHaveBeenCalledWith(
      '/learning/progress',
      expect.objectContaining({ schema: expect.anything() })
    )

    await waitFor(() => expect(screen.getByTestId('progress-value').textContent).toBe('60'))
  })

  it('optimistically updates progress and syncs with API response', async () => {
    putSpy.mockResolvedValueOnce({
      ...learningProgressResponses[0],
      progress_percent: 80,
      last_interaction_at: '2025-01-06T09:00:00Z',
    })

    renderWithProviders(<ProgressProbe />)
    await screen.findByText('mutate')

    fireEvent.click(screen.getByText('mutate'))

    // Optimistic update should reflect immediately.
    await waitFor(() => expect(screen.getByTestId('progress-value').textContent).toBe('80'))

    await waitFor(() => expect(putSpy).toHaveBeenCalledTimes(1))
    expect(putSpy).toHaveBeenCalledWith(
      '/learning/progress/mda_foundations',
      expect.objectContaining({
        body: expect.objectContaining({ progress_percent: 80 }),
        schema: expect.anything(),
      })
    )
  })

  it('surfaces API errors and clears them on dismiss', async () => {
    const apiError = new ApiClientError('unauthorized', 401, {
      error: { message: 'Session expired' },
    })
    putSpy.mockRejectedValue(apiError)

    renderWithProviders(<ProgressProbe />)
    await screen.findByText('mutate')

    fireEvent.click(screen.getByText('mutate'))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('session')

    fireEvent.click(screen.getByText('dismiss'))
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
  })

  it('records walkthrough completions and updates cache', async () => {
    postSpy.mockImplementationOnce(async (path: string) => {
      expect(path).toBe('/learning/progress/mda_foundations/walkthrough-events')
      return {
        ...learningProgressResponses[0],
        progress_percent: 100,
        completed_at: '2025-01-06T10:15:00Z',
        last_interaction_at: '2025-01-06T10:15:00Z',
      }
    })

    renderWithProviders(<ProgressProbe />)
    await screen.findByText('walkthrough')

    fireEvent.click(screen.getByText('walkthrough'))

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith(
        '/learning/progress/mda_foundations/walkthrough-events',
        expect.objectContaining({
          body: expect.objectContaining({ progress_percent: 100, section_key: 'item-7' }),
          schema: expect.anything(),
        })
      )
    )

    await waitFor(() => expect(screen.getByTestId('progress-value').textContent).toBe('100'))
  })

  it('derives dashboard highlights from module sections', async () => {
    renderWithProviders(<HighlightsProbe />)

    const total = await screen.findByTestId('completion-total')
    expect(total.textContent).toBe('2')
    await waitFor(() => expect(screen.getByTestId('sections-in-progress').textContent).toBe('2'))
    await waitFor(() =>
      expect(screen.getByTestId('next-lesson').textContent).toBe(
        'risk_mastery::Item 1A - Risk Factors'
      )
    )
  })

  it('resolves section snapshots for a matching analysis run', async () => {
    renderWithProviders(<SnapshotProbe analysisId="11111111-1111-1111-1111-111111111111" />)

    await waitFor(() => expect(screen.getByTestId('snapshot-percent').textContent).toBe('60'))
    expect(screen.getByTestId('snapshot-status').textContent).toBe('in_progress')
  })

  it('treats unmatched analyses as new runs even when previous completions exist', async () => {
    const nextAnalysisId = '99999999-9999-9999-9999-999999999999'
    const customRecord = JSON.parse(
      JSON.stringify(learningProgressResponses[0])
    ) as (typeof learningProgressResponses)[number]
    customRecord.progress_percent = 100
    customRecord.completed_at = '2024-12-15T09:05:00Z'

    const sections =
      (customRecord.metadata.sections as Record<string, Record<string, unknown>>) ?? {}
    const sectionKey = 'Item 7 - Management Discussion & Analysis'
    const sectionMeta = { ...(sections[sectionKey] ?? {}) }
    sectionMeta['latest_analysis_id'] = nextAnalysisId
    sectionMeta['latest_progress_percent'] = 0
    sectionMeta['last_event_at'] = '2025-01-10T11:00:00Z'
    const analysisRuns =
      (sectionMeta['analysis_runs'] as Record<string, Record<string, unknown>>) ?? {}
    if (analysisRuns[nextAnalysisId]) {
      delete analysisRuns[nextAnalysisId]
    }
    sectionMeta['analysis_runs'] = analysisRuns
    sections[sectionKey] = sectionMeta
    customRecord.metadata.sections = sections

    getSpy.mockResolvedValueOnce([customRecord, learningProgressResponses[1]])

    renderWithProviders(<SnapshotProbe analysisId={nextAnalysisId} />)

    await waitFor(() => expect(screen.getByTestId('snapshot-percent').textContent).toBe('0'))
    expect(screen.getByTestId('snapshot-status').textContent).toBe('queued')
  })
})
