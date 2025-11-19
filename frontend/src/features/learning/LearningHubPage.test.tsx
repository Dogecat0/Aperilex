import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import type * as ReactRouterDomModule from 'react-router-dom'
import { apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import { learningProgressResponses, quizAttemptResponses } from '@/../tests/fixtures/learning'

import { mockPaginatedAnalysesResponse, mockAnalysisDetail } from '@/test/fixtures/analyses'
import { LearningHubPage } from './LearningHubPage'

const mockNavigate = vi.fn()
const getSpy = vi.spyOn(apiClient, 'get')
const postSpy = vi.spyOn(apiClient, 'post')
const latestAnalysisId = mockPaginatedAnalysesResponse.items[0].analysis_id

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<ReactRouterDomModule>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

beforeEach(() => {
  getSpy.mockReset()
  postSpy.mockReset()
  mockNavigate.mockReset()
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

  postSpy.mockImplementation(async (path: string, _opts?: { body?: Record<string, unknown> }) => {
    if (path === '/learning/quiz-attempts') {
      return quizAttemptResponses[0]
    }
    throw new Error(`Unexpected POST path: ${path}`)
  })
})

afterEach(() => {
  getSpy.mockReset()
  postSpy.mockReset()
  mockNavigate.mockReset()
})

describe('LearningHubPage', () => {
  it('renders persisted progress and recent quiz attempts', async () => {
    renderWithProviders(<LearningHubPage />)

    expect(await screen.findByText('60%')).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Score 67%'))).toBeInTheDocument()
    const summarySnippets = await screen.findAllByText(/Connect commentary to margin movements/i)
    expect(summarySnippets.length).toBeGreaterThan(0)
    const resumeButtons = screen.getAllByRole('button', { name: /Resume walkthrough/i })
    expect(resumeButtons.length).toBeGreaterThan(0)
    expect(
      screen.queryByRole('link', { name: /View Management Discussion & Analysis/i })
    ).toBeNull()
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
      expect(screen.queryByRole('button', { name: /Resume walkthrough/i })).toBeNull()
    )
  })

  it('does not render manual completion actions', async () => {
    renderWithProviders(<LearningHubPage />)
    await screen.findByText('60%')
    expect(screen.queryByText('Mark complete')).toBeNull()
  })

  it('navigates directly to the walkthrough analysis when resuming', async () => {
    renderWithProviders(<LearningHubPage />)

    const resumeButtons = await screen.findAllByRole('button', { name: /Resume walkthrough/i })
    fireEvent.click(resumeButtons[0])

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith(
        `/filing/${latestAnalysisId}`,
        expect.objectContaining({
          state: expect.objectContaining({
            focusSection: expect.anything(),
          }),
        })
      )
    )
  })

  it('surfaces automatic logging guidance for quiz attempts', async () => {
    renderWithProviders(<LearningHubPage />)
    expect(await screen.findByText(/automatically log quiz attempts/i)).toBeInTheDocument()
    expect(screen.queryByText('Log practice attempt')).toBeNull()
  })

  it('resets card progress for a fresh analysis even when aggregates are complete', async () => {
    const latestAnalysisIdOverride = '11111111-1111-1111-1111-111111111111'
    const freshProgress = JSON.parse(
      JSON.stringify(learningProgressResponses)
    ) as typeof learningProgressResponses
    const sectionKey = 'Item 7 - Management Discussion & Analysis'
    const sectionMeta = freshProgress[0].metadata.sections?.[sectionKey] as {
      analysis_runs?: Record<string, { progress_percent?: number }>
      latest_progress_percent?: number
      progress_percent?: number
    }
    if (sectionMeta?.analysis_runs?.[latestAnalysisIdOverride]) {
      sectionMeta.analysis_runs[latestAnalysisIdOverride].progress_percent = 0
      sectionMeta.latest_progress_percent = 0
      sectionMeta.progress_percent = 100
    }
    freshProgress[0].progress_percent = 100
    freshProgress[0].completed_at = '2024-12-15T09:05:00Z'

    getSpy.mockImplementation(async (path: string) => {
      if (path === '/learning/progress') {
        return freshProgress
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
          analysis_id: latestAnalysisIdOverride,
          filing_id: mockPaginatedAnalysesResponse.items[0].filing_id,
        }
      }
      throw new Error(`Unexpected GET path: ${path}`)
    })

    renderWithProviders(<LearningHubPage />)

    expect(await screen.findByText('Queued')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})
