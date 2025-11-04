import { act, screen, waitFor, within } from '@testing-library/react'
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

      if (path === '/learning/progress') {
        return [] as unknown
      }

      throw new Error(`Unexpected path: ${path}`)
    })
    vi.spyOn(apiClient, 'post').mockImplementation(
      async (path: string, config?: Record<string, unknown>) => {
        if (path.startsWith('/learning/progress/')) {
          const parts = path.split('/')
          const moduleKey = parts[3] ?? 'unknown-module'
          const body = (config?.body as { progress_percent?: number } | undefined) ?? {}
          const progressPercent =
            typeof body.progress_percent === 'number' ? body.progress_percent : 0
          return {
            schema_version: 1,
            progress_id: `progress-${moduleKey}`,
            user_id: 'user-1',
            module_key: moduleKey,
            progress_percent: progressPercent,
            last_interaction_at: new Date().toISOString(),
            completed_at: progressPercent >= 100 ? new Date().toISOString() : null,
            metadata: {},
            created_at: null,
            updated_at: null,
          }
        }

        throw new Error(`Unexpected post path: ${path}`)
      }
    )
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

    const panelNextButton = await screen.findByRole('button', { name: /^Next section$/i })
    expect(panelNextButton).toBeDisabled()

    const incorrectOption = await screen.findByRole('button', {
      name: /The launch of a one-time licensing settlement./i,
    })
    await user.click(incorrectOption)
    expect(await screen.findByText(/Not quite\. Select a different answer\./i)).toBeInTheDocument()
    expect(panelNextButton).toBeDisabled()

    const correctOption = await screen.findByRole('button', {
      name: /Recurring services growth offsetting hardware softness\./i,
    })
    await user.click(correctOption)

    await waitFor(() => {
      expect(screen.getByText(/1 of 2 sections completed/i)).toBeInTheDocument()
      expect(panelNextButton).toBeDisabled()
    })

    const celebrationDialog = await screen.findByRole('dialog', { name: /Nice work!/i })
    expect(celebrationDialog).toBeInTheDocument()

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/learning/progress/mda_foundations/walkthrough-events',
        expect.objectContaining({
          body: expect.objectContaining({
            progress_percent: 100,
            section_key: 'Item 7 - Management Discussion & Analysis',
          }),
        })
      )
    })

    const closeButton = within(celebrationDialog).getByRole('button', { name: /^Close$/i })
    await user.click(closeButton)

    expect(
      await screen.findByRole('heading', { name: 'Risk Factors Deep Dive' })
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /Regulators continue probing App Store policies, which Apple labels high severity/i
      )
    ).toBeInTheDocument()

    expect(
      screen.getByText(
        /Pro tip: New high-severity highlight detected: Regulation pressure remains elevated\./i
      )
    ).toBeInTheDocument()
    const lessonLink = screen.getByRole('link', {
      name: /Interpreting regulatory risk language/i,
    })
    expect(lessonLink).toHaveAttribute(
      'href',
      '/learning?module=risk_mastery&lesson=lesson-risk-regulation'
    )

    const viewChangesButton = screen.getByRole('button', { name: /View changes/i })
    await user.click(viewChangesButton)

    const diffDrawer = await screen.findByText(/Sentiment shift/i)
    expect(diffDrawer).toBeInTheDocument()
    expect(screen.getAllByText(/Regulation pressure remains elevated/i).length).toBeGreaterThan(1)

    const closeDiffButton = screen.getByRole('button', { name: /^Close$/i })
    await user.click(closeDiffButton)

    const finalNextButton = screen.getByRole('button', { name: /Finished/i })
    expect(finalNextButton).toBeDisabled()

    const riskCorrectOption = await screen.findByRole('button', {
      name: /Potential changes to App Store economics that impact profitability\./i,
    })
    await user.click(riskCorrectOption)

    await waitFor(() => {
      expect(screen.getByText(/2 of 2 sections completed/i)).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/learning/progress/risk_mastery/walkthrough-events',
        expect.objectContaining({
          body: expect.objectContaining({
            progress_percent: 100,
            section_key: 'Item 1A - Risk Factors',
          }),
        })
      )
    })
    const completionDialog = await screen.findByRole('dialog', { name: /Nice work!/i })
    expect(completionDialog).toBeInTheDocument()
    expect(within(completionDialog).getByRole('button', { name: /^Finished$/i })).toBeDisabled()
    const dismissButton = within(completionDialog).getByRole('button', { name: /^Close$/i })
    await user.click(dismissButton)

    expect(apiClient.post).toHaveBeenCalledTimes(2)
    expect(
      screen.getByText(/Walkthrough complete—return to dashboard when ready\./i)
    ).toBeInTheDocument()
  })

  it('respects focus section state by activating the matching walkthrough step', async () => {
    const { router } = renderWithRouter(['/dashboard'])

    await act(async () => {
      await router.navigate(`/filing/${DETAIL_ID}`, {
        state: { focusTab: 'sections', focusSection: 'Risk Factors' },
      })
    })

    expect(
      await screen.findByRole('heading', { name: 'Risk Factors Deep Dive' })
    ).toBeInTheDocument()

    const stepTwoButton = await screen.findByRole('button', { name: /^Step 2/i })
    await waitFor(() => {
      expect(stepTwoButton).toHaveAttribute('aria-current', 'step')
    })
  })

  it('opens the sentiment tab when requested through router state', async () => {
    const { router } = renderWithRouter(['/dashboard'])

    await act(async () => {
      await router.navigate(`/filing/${DETAIL_ID}`, {
        state: { focusTab: 'sentiment' },
      })
    })

    const sentimentTab = await screen.findByRole('tab', { name: /Sentiment/i })
    expect(sentimentTab).toHaveAttribute('aria-selected', 'true')
    expect(
      screen.getByText(/Overall sentiment aggregates guided sections to highlight tone shifts/i)
    ).toBeInTheDocument()
  })
})
