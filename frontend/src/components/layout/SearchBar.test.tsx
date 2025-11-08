import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type * as ReactRouterDomModule from 'react-router-dom'
import { renderWithProviders } from '@/test/utils'
import { SearchBar } from './SearchBar'
import { mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'
import type {
  UseAnalysisSearchOptions,
  UseAnalysisSearchReturn,
} from '@/lib/hooks/useAnalysisSearch'
import type * as HooksModule from '@/lib/hooks'

const mockNavigate = vi.fn()
const mockUseAnalysisSearch = vi.hoisted(() =>
  vi.fn<UseAnalysisSearchReturn, [string, UseAnalysisSearchOptions?]>()
)

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<ReactRouterDomModule>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/lib/hooks', async () => {
  const actual = await vi.importActual<HooksModule>('@/lib/hooks')
  return {
    ...actual,
    useAnalysisSearch: mockUseAnalysisSearch,
  }
})

describe('SearchBar', () => {
  beforeEach(() => {
    mockUseAnalysisSearch.mockReturnValue({
      data: mockPaginatedAnalysesResponse,
      isFetching: false,
      error: null,
      isStale: false,
      isLoading: false,
      status: 'success',
      fetchStatus: 'idle',
    } as unknown as UseAnalysisSearchReturn)
  })

  afterEach(() => {
    mockNavigate.mockReset()
    mockUseAnalysisSearch.mockReset()
  })

  it('shows filing search results and navigates on selection', async () => {
    const user = userEvent.setup()

    renderWithProviders(<SearchBar />)

    const input = screen.getByPlaceholderText(/search filings/i)
    await user.click(input)
    await user.type(input, 'Apple')

    const resultButton = await screen.findByRole('button', { name: /apple inc\./i })
    await user.click(resultButton)

    expect(mockNavigate).toHaveBeenCalledWith('/filing/11111111-1111-1111-1111-111111111111')
  })
})
