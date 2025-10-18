import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import { DashboardPage } from './DashboardPage'
import { apiClient } from '@/lib/apiClient'
import { mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'
import { learningProgressResponses } from '@/../tests/fixtures/learning'

const mockTaskResponse = {
  schema_version: 1,
  task_id: 'task-123',
  status: 'QUEUED',
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (path: string) => {
      if (path === '/learning/progress') {
        return learningProgressResponses
      }
      if (path === '/analyses') {
        return mockPaginatedAnalysesResponse
      }
      throw new Error(`Unexpected GET path: ${path}`)
    })
    vi.spyOn(apiClient, 'post').mockResolvedValue(mockTaskResponse)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders learning-first hero and recent analyses from library data', async () => {
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText(/Learning-first progress snapshot/i)).toBeInTheDocument()
    expect(await screen.findByText(/Continue where you left off/i)).toBeInTheDocument()
    expect(screen.getByText('3d')).toBeInTheDocument()
    expect(screen.getByText('0/3 complete')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /KPI extract/i })).toBeInTheDocument()

    expect(screen.getByText(/Recent analyses/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View analysis/i })).toBeInTheDocument()
  })

  it('triggers practice commands from the continuation rail', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    const kpiButton = await screen.findByRole('button', { name: /KPI extract/i })
    await user.click(kpiButton)

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        expect.stringMatching(/\/practice\/kpi-extract$/),
        expect.objectContaining({
          schema: expect.anything(),
        })
      )
    })
  })

  it('requests new data when changing library filters', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    await screen.findByText(/Learning-first progress snapshot/i)

    const filterButton = screen.getByRole('button', { name: /Flagged follow-up/i })
    await user.click(filterButton)

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/analyses',
        expect.objectContaining({
          query: expect.objectContaining({
            segment: 'flagged',
          }),
        })
      )
    })
  })
})
