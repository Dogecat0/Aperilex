import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import type { AuthSession, AuthStatus } from '@/state/authStore'
import type { FilingSearchResult } from '@/lib/types/filing'
import { FilingDetailPanel } from './FilingDetailPanel'
import type { AnalysisTemplateOption } from './FilingDetailPanel'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '@/hooks/useAuth'

interface MockedAuthState {
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

const filing: FilingSearchResult = {
  schema_version: 1,
  accession_number: '0000320193-24-000001',
  cik: '0000320193',
  company_name: 'Aperilex Test Corp',
  filing_date: '2024-01-01',
  filing_id: '00000000-0000-0000-0000-000000000001',
  filing_type: '10-Q',
  has_content: true,
  sections_count: 4,
  ticker: 'APXL',
}

const templateOptions: AnalysisTemplateOption[] = [
  { value: 'comprehensive', label: 'Comprehensive' },
  { value: 'financial_focused', label: 'Financial focus' },
]

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

describe('FilingDetailPanel analyze CTA', () => {
  beforeEach(() => {
    useAuthMock.mockReset()
  })

  it('executes analyze handler when authenticated', async () => {
    const onAnalyze = vi.fn()

    useAuthMock.mockReturnValue(buildAuthState())

    renderWithProviders(
      <FilingDetailPanel
        searchResult={filing}
        onAnalyze={onAnalyze}
        isAnalyzeDisabled={false}
        isAnalyzing={false}
        analysisTemplate="comprehensive"
        templateOptions={templateOptions}
        onTemplateChange={() => {}}
      />
    )

    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /Analyze this filing/i }))

    expect(onAnalyze).toHaveBeenCalledTimes(1)
  })

  it('prompts login instead of running analyze when anonymous', async () => {
    const loginWithGoogle = vi.fn()
    const onAnalyze = vi.fn()

    useAuthMock.mockReturnValue(
      buildAuthState({
        status: 'unauthenticated',
        isAuthenticated: false,
        session: null,
        loginWithGoogle,
      })
    )

    renderWithProviders(
      <FilingDetailPanel
        searchResult={filing}
        onAnalyze={onAnalyze}
        isAnalyzeDisabled={false}
        isAnalyzing={false}
        analysisTemplate="comprehensive"
        templateOptions={templateOptions}
        onTemplateChange={() => {}}
      />
    )

    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /Analyze this filing/i }))

    expect(onAnalyze).not.toHaveBeenCalled()
    expect(loginWithGoogle).toHaveBeenCalledTimes(1)
  })
})
