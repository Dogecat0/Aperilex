import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/lib/apiClient'
import { mockAnalysisDetail, mockPaginatedAnalysesResponse } from '@/test/fixtures/analyses'
import { renderWithRouter } from '@/test/utils'
import type { AuthSession, AuthStatus } from '@/state/authStore'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '@/hooks/useAuth'

type MockedAuthState = {
  status: AuthStatus
  session: AuthSession | null
  accessToken: string | null
  accessTokenExpiresAt: number | null
  isAuthenticated: boolean
  lastError: string | null
  loginWithGoogle: (redirectTo?: string) => void
  completeCallback: () => Promise<{ redirectTo: string | null }>
  logout: () => void | Promise<void>
  refreshSession: () => void | Promise<void>
  requireSession: () => AuthSession
}

const useAuthMock = useAuth as unknown as vi.Mock<[], MockedAuthState>

const baseSession: AuthSession = {
  user: {
    id: 'user-1',
    email: 'user@example.com',
    tier: null,
    permissions: [],
  },
  issuedAt: null,
  refreshExpiresAt: null,
}

const buildAuthState = (overrides: Partial<MockedAuthState> = {}): MockedAuthState => ({
  status: 'authenticated',
  session: baseSession,
  isAuthenticated: true,
  accessToken: 'token',
  accessTokenExpiresAt: Date.now() + 60_000,
  lastError: null,
  loginWithGoogle: vi.fn(),
  logout: vi.fn(),
  completeCallback: vi.fn(async () => ({ redirectTo: null })),
  refreshSession: vi.fn(),
  requireSession: vi.fn(() => baseSession),
  ...overrides,
})

const DETAIL_ID = mockAnalysisDetail.analysis_id

describe('FilingDetailPage', () => {
  beforeEach(() => {
    useAuthMock.mockReset()
    useAuthMock.mockReturnValue(buildAuthState())
    vi.spyOn(apiClient, 'get').mockImplementation(async (path: string) => {
      if (path.startsWith('/analyses/')) {
        return mockAnalysisDetail as unknown
      }

      if (path === '/analyses') {
        return mockPaginatedAnalysesResponse as unknown
      }

      throw new Error(`Unexpected path: ${path}`)
    })
  })

  afterEach(() => {
    useAuthMock.mockReset()
    vi.restoreAllMocks()
  })

  it('renders the guided walkthrough header and first section', async () => {
    renderWithRouter([`/filing/${DETAIL_ID}`])

    expect(await screen.findByRole('heading', { name: 'Apple Inc.' })).toBeInTheDocument()
    expect(screen.getByText(/Guided Filing • 10-Q/i)).toBeInTheDocument()
    expect(screen.getByText(/0 of 2 sections completed/i)).toBeInTheDocument()

    expect(await screen.findByRole('heading', { name: 'MD&A Guided Review' })).toBeInTheDocument()
    expect(screen.getByText('Services pacing profit growth')).toBeInTheDocument()
    expect(
      screen.getByText('Recurring services growth offsetting hardware softness.')
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        `/analyses/${DETAIL_ID}`,
        expect.objectContaining({
          query: expect.objectContaining({ include_full_results: true }),
        })
      )
    })
  })

  it('requires correct comprehension responses before advancing', async () => {
    const user = userEvent.setup()
    renderWithRouter([`/filing/${DETAIL_ID}`])

    const nextButton = await screen.findByRole('button', { name: /Next section/i })
    expect(nextButton).toBeDisabled()

    const incorrectOption = await screen.findByRole('button', {
      name: /The launch of a one-time licensing settlement./i,
    })
    await user.click(incorrectOption)
    expect(await screen.findByText(/Not quite\. Select a different answer\./i)).toBeInTheDocument()
    expect(nextButton).toBeDisabled()

    const correctOption = await screen.findByRole('button', {
      name: /Recurring services growth offsetting hardware softness\./i,
    })
    await user.click(correctOption)

    await waitFor(() => {
      expect(screen.getByText(/Explanation/i)).toBeInTheDocument()
      expect(screen.getByText(/1 of 2 sections completed/i)).toBeInTheDocument()
      expect(nextButton).not.toBeDisabled()
    })

    await user.click(nextButton)

    expect(
      await screen.findByRole('heading', { name: 'Risk Factors Deep Dive' })
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /Regulators continue probing App Store policies, which Apple labels high severity/i
      )
    ).toBeInTheDocument()
    const finalNextButton = screen.getByRole('button', { name: /Finished/i })
    expect(finalNextButton).toBeDisabled()

    const riskCorrectOption = await screen.findByRole('button', {
      name: /Potential changes to App Store economics that impact profitability\./i,
    })
    await user.click(riskCorrectOption)

    await waitFor(() => {
      expect(screen.getByText(/2 of 2 sections completed/i)).toBeInTheDocument()
    })
    expect(
      screen.getByText(/Walkthrough complete—return to dashboard when ready\./i)
    ).toBeInTheDocument()
  })
})
