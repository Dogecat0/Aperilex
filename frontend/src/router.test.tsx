import { cleanup, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

beforeEach(() => {
  useAuthMock.mockReset()
})

describe('App routing', () => {
  it('redirects root to dashboard for authenticated users', async () => {
    useAuthMock.mockReturnValue(buildAuthState())

    const { router } = renderWithRouter(['/'])

    await screen.findByText('Filing intelligence at a glance')

    expect(router.state.location.pathname).toBe('/dashboard')
  })

  it('redirects anonymous visitors to the login route', async () => {
    useAuthMock.mockReturnValue(
      buildAuthState({
        status: 'unauthenticated',
        isAuthenticated: false,
        session: null,
      })
    )

    const protectedPaths = ['/dashboard', '/analyze', '/learn', '/saved', '/filing/demo-analysis']

    for (const path of protectedPaths) {
      cleanup()
      const { router } = renderWithRouter([path])

      await screen.findByRole('heading', { name: 'Sign in to sync your insights' })
      expect(router.state.location.pathname).toBe('/login')
    }
  })

  it('shows a spinner while the session is initializing', async () => {
    useAuthMock.mockReturnValue(
      buildAuthState({
        status: 'initializing',
        isAuthenticated: false,
        session: null,
      })
    )

    renderWithRouter(['/dashboard'])

    await screen.findByTestId('full-screen-spinner')
  })

  it('navigates between primary routes when authenticated', async () => {
    useAuthMock.mockReturnValue(buildAuthState())

    const user = userEvent.setup()

    renderWithRouter(['/dashboard'])

    await screen.findByText('Filing intelligence at a glance')

    await user.click(await screen.findByRole('link', { name: 'Learn' }))
    await screen.findByText('Build your filing fluency')

    await user.click(await screen.findByRole('link', { name: 'Saved' }))
    await screen.findByText('Keep your research within reach')
  })

})
