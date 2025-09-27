import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import { SearchBar } from './SearchBar'
import { apiClient } from '@/lib/apiClient'
import { mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('SearchBar', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue(mockPaginatedAnalysesResponse)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    mockNavigate.mockReset()
  })

  it('shows filing search results and navigates on selection', async () => {
    const user = userEvent.setup()

    renderWithProviders(<SearchBar />)

    const input = screen.getByPlaceholderText(/search filings/i)
    await user.click(input)
    await user.type(input, 'Apple')

    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 450))
    })

    const resultButton = await screen.findByRole('button', { name: /apple inc\./i })
    await user.click(resultButton)

    expect(mockNavigate).toHaveBeenCalledWith('/filing/11111111-1111-1111-1111-111111111111')
  })
})
