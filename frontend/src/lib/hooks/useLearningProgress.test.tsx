import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import { learningProgressResponses } from '@/../tests/fixtures/learning'
import { useLearningProgress } from './useLearningProgress'

const getSpy = vi.spyOn(apiClient, 'get')
const putSpy = vi.spyOn(apiClient, 'put')
const postSpy = vi.spyOn(apiClient, 'post')

function ProgressProbe() {
  const {
    progress,
    updateProgress,
    recordWalkthroughEvent,
    scheduleReview,
    error,
    clearError,
  } = useLearningProgress()
  const record = progress.find((item) => item.moduleKey === 'mda-101')

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
            moduleKey: 'mda-101',
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
            moduleKey: 'mda-101',
            sectionKey: 'item-7',
            progressPercent: 100,
            completedAt: '2025-01-06T10:15:00Z',
          }).catch(() => {})
        }
      >
        walkthrough
      </button>
      <button
        type="button"
        onClick={() =>
          void scheduleReview({
            moduleKey: 'mda-101',
            pendingReviewCount: 2,
            scheduledFor: '2025-01-07T09:00:00Z',
          }).catch(() => {})
        }
      >
        schedule
      </button>
    </div>
  )
}

describe('useLearningProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
      '/learning/progress/mda-101',
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
      expect(path).toBe('/learning/progress/mda-101/walkthrough-events')
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

    await waitFor(() => expect(postSpy).toHaveBeenCalledWith(
      '/learning/progress/mda-101/walkthrough-events',
      expect.objectContaining({
        body: expect.objectContaining({ progress_percent: 100, section_key: 'item-7' }),
        schema: expect.anything(),
      })
    ))

    await waitFor(() => expect(screen.getByTestId('progress-value').textContent).toBe('100'))
  })

  it('schedules reviews and merges progress updates', async () => {
    postSpy.mockImplementationOnce(async (path: string) => {
      expect(path).toBe('/learning/progress/mda-101/reviews/schedule')
      return {
        ...learningProgressResponses[0],
        metadata: { ...learningProgressResponses[0].metadata, pending_review_count: 2 },
        updated_at: '2025-01-06T11:00:00Z',
      }
    })

    renderWithProviders(<ProgressProbe />)
    await screen.findByText('schedule')

    fireEvent.click(screen.getByText('schedule'))

    await waitFor(() => expect(postSpy).toHaveBeenCalledWith(
      '/learning/progress/mda-101/reviews/schedule',
      expect.objectContaining({
        body: expect.objectContaining({ pending_review_count: 2 }),
        schema: expect.anything(),
      })
    ))

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledTimes(1)
    )

    expect(screen.getByTestId('progress-value').textContent).toBe('60')
  })
})
