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
    expect(screen.getAllByText(/Completed analyses/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Companies analyzed/i)).toBeInTheDocument()
    expect(screen.getByText(/Latest completion/i)).toBeInTheDocument()
    expect(await screen.findByText(/Continue where you left off/i)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Resume walkthrough/i }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /KPI extract/i })).not.toBeInTheDocument()

    expect(screen.getByText(/Recent analyses/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View latest/i })).toBeInTheDocument()
  })

  it('requests new data when changing library filters', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    await screen.findByText(/Stay on top of your filings/i)

    const searchInput = screen.getByLabelText(/company or ticker/i)
    await user.type(searchInput, 'AAPL')

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        '/analyses',
        expect.objectContaining({
          query: expect.objectContaining({
            search: expect.stringContaining('AAPL'),
          }),
        })
      )
    })
  })
})
