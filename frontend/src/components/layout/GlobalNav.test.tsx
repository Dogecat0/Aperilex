import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type * as ThemeTokensModule from '@/styles/tokens'
import { GlobalNav } from './GlobalNav'
import { useAppStore } from '@/lib/store'

vi.mock('@/components/ThemeProvider', async () => {
  const tokensModule = await vi.importActual<ThemeTokensModule>('@/styles/tokens')
  return {
    useThemeTokens: () => tokensModule.lightTokens,
  }
})

const loginMock = vi.fn()
const logoutMock = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    status: 'unauthenticated',
    isAuthenticated: false,
    session: null,
    accessToken: null,
    accessTokenExpiresAt: null,
    lastError: null,
    loginWithGoogle: loginMock,
    logout: logoutMock,
    completeCallback: vi.fn(),
    refreshSession: vi.fn(),
    requireSession: vi.fn(),
  })),
}))

const { useAuth } = await import('@/hooks/useAuth')

beforeEach(() => {
  loginMock.mockReset()
  logoutMock.mockReset()
  ;(useAuth as unknown as vi.Mock).mockReset()
})

describe('GlobalNav authentication controls', () => {
  it('renders sign-in button when anonymous', async () => {
    useAppStore.setState((state) => ({ ...state, theme: 'light' }))
    const mockUseAuth = useAuth as unknown as vi.Mock
    mockUseAuth.mockImplementation(() => ({
      status: 'unauthenticated',
      isAuthenticated: false,
      session: null,
      accessToken: null,
      accessTokenExpiresAt: null,
      lastError: null,
      loginWithGoogle: loginMock,
      logout: logoutMock,
      completeCallback: vi.fn(),
      refreshSession: vi.fn(),
      requireSession: vi.fn(),
    }))

    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/learn']}>
        <GlobalNav />
      </MemoryRouter>
    )

    const loginButton = await screen.findByRole('button', { name: /sign in/i })
    expect(loginButton).toBeInTheDocument()

    await user.click(loginButton)
    expect(loginMock).toHaveBeenCalledWith('/learn')
  })

  it('shows user email and logout control when authenticated', async () => {
    useAppStore.setState((state) => ({ ...state, theme: 'light' }))
    const mockUseAuth = useAuth as unknown as vi.Mock
    mockUseAuth.mockImplementation(() => ({
      status: 'authenticated',
      isAuthenticated: true,
      session: {
        user: {
          id: 'user-1',
          email: 'investor@example.com',
          tier: 'BASIC',
          permissions: [],
        },
        issuedAt: Date.now(),
        refreshExpiresAt: Date.now() + 3600_000,
      },
      accessToken: 'token',
      accessTokenExpiresAt: Date.now() + 180_000,
      lastError: null,
      loginWithGoogle: loginMock,
      logout: logoutMock,
      completeCallback: vi.fn(),
      refreshSession: vi.fn(),
      requireSession: vi.fn(),
    }))

    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <GlobalNav />
      </MemoryRouter>
    )

    expect(await screen.findByText('investor@example.com')).toBeInTheDocument()

    const logoutButton = await screen.findByRole('button', { name: /sign out/i })
    await user.click(logoutButton)

    expect(logoutMock).toHaveBeenCalled()
  })
})
