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

  it('renders summary cards and insight stream from analyses data', async () => {
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText('Apple Inc. • 10-Q')).toBeInTheDocument()
    expect(screen.getByText(/87% confidence/i)).toBeInTheDocument()
    expect(screen.getByText(/Insights ready/i)).toBeInTheDocument()

    expect(
      screen.getByText('Margin expansion driven by disciplined expense control and services mix.')
    ).toBeInTheDocument()
    expect(screen.getByText(/Supply chain remains a watchpoint/i)).toBeInTheDocument()
  })

  it('requests new data when changing filter toggles', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DashboardPage />)

    await screen.findByText('Apple Inc. • 10-Q')

    const filterButton = screen.getByRole('button', { name: /Risk Signals/i })
    await user.click(filterButton)

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith('/analyses', expect.objectContaining({
        query: expect.objectContaining({
          analysis_type: 'RISK',
          analysis_template: 'financial_focused',
        }),
      }))
    })
  })
})
