import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import { DashboardPage } from './DashboardPage'
import { apiClient } from '@/lib/apiClient'
import { mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (path: string) => {
      if (path === '/analyses') {
        return mockPaginatedAnalysesResponse
      }
      throw new Error(`Unexpected GET path: ${path}`)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders filings-focused hero and recent analyses from library data', async () => {
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText(/Stay on top of your filings/i)).toBeInTheDocument()
    expect(screen.getByText(/Completed analyses/i)).toBeInTheDocument()
    expect(screen.getByText(/Guided sections covered/i)).toBeInTheDocument()
    expect(screen.getByText(/Latest completion/i)).toBeInTheDocument()
    expect(await screen.findByText(/Continue where you left off/i)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Resume walkthrough/i }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /KPI extract/i })).not.toBeInTheDocument()

    expect(screen.getByText(/Recent analyses/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View analysis/i })).toBeInTheDocument()
  })

  it('requests new data when changing library filters', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    await screen.findByText(/Stay on top of your filings/i)

    const filterButton = screen.getByRole('button', { name: /10-q snapshot/i })
    await user.click(filterButton)

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/analyses',
        expect.objectContaining({
          query: expect.objectContaining({
            search: '10-Q',
          }),
        })
      )
    })
  })
})
