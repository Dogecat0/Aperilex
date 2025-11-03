import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import { learningProgressResponses, quizAttemptResponses } from '@/../tests/fixtures/learning'

const moduleBindingsResponse = [
  {
    schema_version: 1,
    binding_id: 'binding-1',
    walkthrough_section_id: 'section-1',
    artifact_id: 'artifact-1',
    artifact_type: 'COMPREHENSION_CHECK',
    lesson_id: 'lesson-1',
    learning_module_key: 'mda_foundations',
    module_stage: 'fundamentals',
    lesson_title: 'Margin quiz',
    status: 'APPROVED',
    last_reviewed_at: '2025-01-05T12:00:00Z',
    updated_at: '2025-01-05T12:00:00Z',
  },
]
import { mockPaginatedAnalysesResponse, mockAnalysisDetail } from '@/test/fixtures/analyses'
import { LearningHubPage } from './LearningHubPage'

const getSpy = vi.spyOn(apiClient, 'get')
const putSpy = vi.spyOn(apiClient, 'put')
const postSpy = vi.spyOn(apiClient, 'post')
const latestAnalysisId = mockPaginatedAnalysesResponse.items[0].analysis_id

beforeEach(() => {
  getSpy.mockReset()
  putSpy.mockReset()
  postSpy.mockReset()
  getSpy.mockImplementation(async (path: string) => {
    if (path === '/learning/progress') {
      return learningProgressResponses
    }
    if (path === '/learning/quiz-attempts') {
      return quizAttemptResponses
    }
    if (path === '/analyses') {
      return mockPaginatedAnalysesResponse
    }
    if (path === `/analyses/${latestAnalysisId}`) {
      return {
        ...mockAnalysisDetail,
        analysis_id: latestAnalysisId,
        filing_id: mockPaginatedAnalysesResponse.items[0].filing_id,
      }
    }
    if (path === '/learning/modules/mda_foundations/bindings') {
      return moduleBindingsResponse
    }
    throw new Error(`Unexpected GET path: ${path}`)
  })

  putSpy.mockResolvedValue({
    ...learningProgressResponses[0],
    progress_percent: 100,
    completed_at: '2025-01-06T12:00:00Z',
    last_interaction_at: '2025-01-06T12:00:00Z',
  })

  postSpy.mockImplementation(async (path: string, options?: { body?: Record<string, unknown> }) => {
    if (path === '/learning/quiz-attempts') {
      return quizAttemptResponses[0]
    }
    if (path === '/learning/progress/mda_foundations/reviews/schedule') {
      const pendingCount = options?.body?.pending_review_count ?? 1
      const scheduledFor = options?.body?.scheduled_for ?? '2025-01-07T09:00:00Z'
      return {
        ...learningProgressResponses[0],
        pending_review_count: pendingCount,
        last_reviewed_at: scheduledFor,
        metadata: {
          ...learningProgressResponses[0].metadata,
          next_review_at: scheduledFor,
        },
      }
    }
    throw new Error(`Unexpected POST path: ${path}`)
  })
})

afterEach(() => {
  getSpy.mockReset()
  putSpy.mockReset()
  postSpy.mockReset()
})

describe('LearningHubPage', () => {
  it('renders persisted progress and recent quiz attempts', async () => {
    renderWithProviders(<LearningHubPage />)

    expect(await screen.findByText('60% complete')).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Score 67%'))).toBeInTheDocument()
    const summarySnippets = await screen.findAllByText(/Connect commentary to margin movements/i)
    expect(summarySnippets.length).toBeGreaterThan(0)
    const detailLink = screen.getByRole('link', {
      name: /View Management Discussion & Analysis/i,
    })
    expect(detailLink).toHaveAttribute('href', `/filing/${latestAnalysisId}`)
  })

  it('shows onboarding guidance when no analyses exist', async () => {
    const emptyPaginatedAnalyses = {
      schema_version: 2,
      items: [],
      pagination: {
        schema_version: 1,
        page: 1,
        page_size: 8,
        total_items: 0,
        total_pages: 0,
        has_next: false,
        has_previous: false,
        next_page: null,
        previous_page: null,
      },
    }

    getSpy.mockImplementation(async (path: string) => {
      if (path === '/learning/progress') {
        return []
      }
      if (path === '/learning/quiz-attempts') {
        return []
      }
      if (path === '/analyses') {
        return emptyPaginatedAnalyses
      }
      throw new Error(`Unexpected GET path: ${path}`)
    })

    renderWithProviders(<LearningHubPage />)

    expect(
      await screen.findByText(/Launch a filing analysis from the dashboard/i)
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Resume module/i })).toBeNull()
    )
  })

  it('marks a module complete via the optimistic update flow', async () => {
    renderWithProviders(<LearningHubPage />)
    await screen.findByText('60% complete')

    const actionButtons = screen.getAllByText('Mark complete')
    fireEvent.click(actionButtons[0])

    await waitFor(() => expect(putSpy).toHaveBeenCalledTimes(1))
    expect(putSpy).toHaveBeenCalledWith(
      '/learning/progress/mda_foundations',
      expect.objectContaining({
        body: expect.objectContaining({ progress_percent: 100 }),
      })
    )

    await waitFor(() => expect(screen.getByText('100% complete')).toBeInTheDocument())
  })

  it('surfaces toast errors when progress updates fail', async () => {
    putSpy.mockRejectedValue(
      new ApiClientError('unauthorized', 401, { error: { message: 'Session expired' } })
    )

    renderWithProviders(<LearningHubPage />)
    await screen.findByText('60% complete')

    const actionButtons = screen.getAllByText('Mark complete')
    fireEvent.click(actionButtons[0])

    const alert = await screen.findByRole('status')
    expect(alert.textContent).toContain('session')

    const dismissButtons = screen.getAllByText('Dismiss')
    fireEvent.click(dismissButtons[0])
    await waitFor(() => expect(screen.queryByRole('status')).toBeNull())
  })

  it('opens the module modal and schedules a review', async () => {
    renderWithProviders(<LearningHubPage />)

    const resumeButtons = await screen.findAllByRole('button', { name: /Resume module/i })
    fireEvent.click(resumeButtons[0])

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(screen.getByText(/Micro-lessons & review queue/i)).toBeInTheDocument()

    const reviewInput = screen.getByLabelText(/Review date/i)
    fireEvent.change(reviewInput, { target: { value: '2025-01-09' } })

    fireEvent.click(screen.getByRole('button', { name: /Schedule review/i }))

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith(
        '/learning/progress/mda_foundations/reviews/schedule',
        expect.objectContaining({
          body: expect.objectContaining({ pending_review_count: 2 }),
        })
      )
    )
  })

  it('records a practice attempt through the CTA', async () => {
    renderWithProviders(<LearningHubPage />)
    await screen.findByText('Log practice attempt')

    fireEvent.click(screen.getByText('Log practice attempt'))

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1))
    expect(postSpy).toHaveBeenCalledWith(
      '/learning/quiz-attempts',
      expect.objectContaining({
        schema: expect.anything(),
        body: expect.objectContaining({ quiz_id: 'practice-check' }),
      })
    )
  })
})
