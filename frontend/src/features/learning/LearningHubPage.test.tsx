import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import {
  learningProgressResponses,
  quizAttemptResponses,
} from '@/../tests/fixtures/learning'
import { mockPaginatedAnalysesResponse, mockAnalysisDetail } from '@/test/fixtures/analyses'
import { MemoryRouter } from 'react-router-dom'
import { LearningHubPage } from './LearningHubPage'

const getSpy = vi.spyOn(apiClient, 'get')
const putSpy = vi.spyOn(apiClient, 'put')
const postSpy = vi.spyOn(apiClient, 'post')
const latestAnalysisId = mockPaginatedAnalysesResponse.items[0].analysis_id

beforeEach(() => {
  vi.clearAllMocks()
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
    throw new Error(`Unexpected GET path: ${path}`)
  })

  putSpy.mockResolvedValue({
    ...learningProgressResponses[0],
    progress_percent: 100,
    completed_at: '2025-01-06T12:00:00Z',
    last_interaction_at: '2025-01-06T12:00:00Z',
  })

  postSpy.mockResolvedValue(quizAttemptResponses[0])
})

afterEach(() => {
  getSpy.mockReset()
  putSpy.mockReset()
  postSpy.mockReset()
})

describe('LearningHubPage', () => {
  it('renders persisted progress and recent quiz attempts', async () => {
    renderWithProviders(
      <MemoryRouter>
        <LearningHubPage />
      </MemoryRouter>
    )

    expect(await screen.findByText('60% complete')).toBeInTheDocument()
    expect(
      screen.getByText((content) => content.includes('Score 67%'))
    ).toBeInTheDocument()
    const summarySnippets = await screen.findAllByText(/Margin expansion stems/)
    expect(summarySnippets.length).toBeGreaterThan(0)
    const detailLink = screen.getByRole('link', {
      name: /View Management Discussion & Analysis/i,
    })
    expect(detailLink).toHaveAttribute('href', `/filing/${latestAnalysisId}`)
  })

  it('marks a module complete via the optimistic update flow', async () => {
    renderWithProviders(
      <MemoryRouter>
        <LearningHubPage />
      </MemoryRouter>
    )
    await screen.findByText('60% complete')

    const actionButtons = screen.getAllByText('Mark complete')
    fireEvent.click(actionButtons[0])

    await waitFor(() => expect(putSpy).toHaveBeenCalledTimes(1))
    expect(putSpy).toHaveBeenCalledWith(
      '/learning/progress/mda-101',
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

    renderWithProviders(
      <MemoryRouter>
        <LearningHubPage />
      </MemoryRouter>
    )
    await screen.findByText('60% complete')

    const actionButtons = screen.getAllByText('Mark complete')
    fireEvent.click(actionButtons[0])

    const alert = await screen.findByRole('status')
    expect(alert.textContent).toContain('session')

    const dismissButtons = screen.getAllByText('Dismiss')
    fireEvent.click(dismissButtons[0])
    await waitFor(() => expect(screen.queryByRole('status')).toBeNull())
  })

  it('records a practice attempt through the CTA', async () => {
    renderWithProviders(
      <MemoryRouter>
        <LearningHubPage />
      </MemoryRouter>
    )
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
