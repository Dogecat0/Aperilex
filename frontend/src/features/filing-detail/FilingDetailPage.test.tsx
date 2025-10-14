import { screen, waitFor, within } from '@testing-library/react'
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

  it('renders overview stats and curated summary cards', async () => {
    renderWithRouter([`/filing/${DETAIL_ID}`])

    expect(await screen.findByText('Quick read')).toBeInTheDocument()
    expect(screen.getByText('Quick read')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /more/i }).length).toBeGreaterThan(0)
    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByText('Coverage')).toBeInTheDocument()
    expect(screen.getByText('3 sections')).toBeInTheDocument()

    expect(screen.getByText('Key insights')).toBeInTheDocument()
    expect(screen.getByText(/Services revenue accelerated/i)).toBeInTheDocument()
    const criticalFindingsSection = screen.getByText('Critical findings').closest('article')
    expect(criticalFindingsSection).not.toBeNull()
    expect(
      within(criticalFindingsSection as HTMLElement).getAllByRole('listitem').length
    ).toBeGreaterThan(0)
    expect(screen.getByText('Opportunities')).toBeInTheDocument()
    expect(screen.queryByText(/Risk highlights/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Insight timeline/i)).not.toBeInTheDocument()

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith(
        `/analyses/${DETAIL_ID}`,
        expect.objectContaining({
          query: expect.objectContaining({ include_full_results: true }),
        })
      )
    })
  })

  it('supports tab navigation and section quick actions', async () => {
    const user = userEvent.setup()
    renderWithRouter([`/filing/${DETAIL_ID}`])

    const sectionsCardHeading = await screen.findByText('Where to focus')
    const sectionsCard = sectionsCardHeading.closest('article')
    expect(sectionsCard).not.toBeNull()
    await user.click(within(sectionsCard as HTMLElement).getByRole('button', { name: /more/i }))

    const sectionsTab = screen.getByRole('tab', { name: /Sections/i })
    expect(sectionsTab).toHaveAttribute('aria-selected', 'true')

    const explainToggle = (await screen.findAllByRole('button', { name: /Explain more/i }))[0]
    await user.click(explainToggle)

    expect(screen.getByRole('button', { name: /Hide details/i })).toBeInTheDocument()

    const numbersTab = screen.getByRole('tab', { name: /Numbers/i })
    await user.click(numbersTab)

    expect(await screen.findByText(/Total Revenue/i)).toBeInTheDocument()
    expect(screen.getByText('Operating Margin')).toBeInTheDocument()

    expect(screen.queryByRole('tab', { name: /Raw/i })).not.toBeInTheDocument()
  })

  it('highlights sentiment cards and clears focus state', async () => {
    const user = userEvent.setup()
    renderWithRouter([`/filing/${DETAIL_ID}`])

    await screen.findByText('Quick read')

    await user.click(screen.getByRole('tab', { name: /Sections/i }))
    const explainToggle = (await screen.findAllByRole('button', { name: /Explain more/i }))[0]
    await user.click(explainToggle)

    await user.click(screen.getByRole('tab', { name: /Sentiment/i }))
    expect(
      await screen.findByText(/Focused on Management Discussion & Analysis/i)
    ).toBeInTheDocument()
    expect(screen.getByText(/Average sentiment/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Clear focus/i }))
    await waitFor(() => {
      expect(screen.queryByText(/Focused on/i)).not.toBeInTheDocument()
    })
  })
})
