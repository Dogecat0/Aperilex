import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import {
  learningProgressResponses,
  quizAttemptResponses,
} from '@/../tests/fixtures/learning'
import { LearningHubPage } from './LearningHubPage'

const getSpy = vi.spyOn(apiClient, 'get')
const putSpy = vi.spyOn(apiClient, 'put')
const postSpy = vi.spyOn(apiClient, 'post')

beforeEach(() => {
  vi.clearAllMocks()
  getSpy.mockImplementation(async (path: string) => {
    if (path === '/learning/progress') {
      return learningProgressResponses
    }
    if (path === '/learning/quiz-attempts') {
      return quizAttemptResponses
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
    renderWithProviders(<LearningHubPage />)

    await waitFor(() => expect(getSpy).toHaveBeenCalledTimes(2))

    expect(await screen.findByText('60% complete')).toBeInTheDocument()
    expect(
      screen.getByText((content) => content.includes('Score 67%'))
    ).toBeInTheDocument()
  })

  it('marks a module complete via the optimistic update flow', async () => {
    renderWithProviders(<LearningHubPage />)
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
