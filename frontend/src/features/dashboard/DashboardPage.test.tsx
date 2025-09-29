import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import { DashboardPage } from './DashboardPage'
import { apiClient } from '@/lib/apiClient'
import { mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue(mockPaginatedAnalysesResponse)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders summary highlights and recent analyses from library data', async () => {
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText(/Analyses in view/i)).toBeInTheDocument()
    expect(screen.getByText(/1 with confidence scores/i)).toBeInTheDocument()
    expect(screen.getByText(/Average confidence/i)).toBeInTheDocument()
    expect(screen.getByText('87%')).toBeInTheDocument()

    expect(screen.getByText(/Recent analyses/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View analysis/i })).toBeInTheDocument()
  })

  it('requests new data when changing library filters', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    await screen.findByText(/Analyses in view/i)

    const filterButton = screen.getByRole('button', { name: /Flagged follow-up/i })
    await user.click(filterButton)

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith('/analyses', expect.objectContaining({
        query: expect.objectContaining({
          segment: 'flagged',
        }),
      }))
    })
  })
})
