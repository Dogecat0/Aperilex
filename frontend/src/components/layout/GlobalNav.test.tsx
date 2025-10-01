import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GlobalNav } from './GlobalNav'
import { useAppStore } from '@/lib/store'

vi.mock('@/components/ThemeProvider', () => {
  const tokens = {
    name: 'light' as const,
    sentiment: { positive: '#22c55e', neutral: '#6366f1', negative: '#ef4444' },
    colors: {
      background: '#fff',
      surface: '#fff',
      surfaceMuted: '#f4f4f4',
      foreground: '#111827',
      foregroundMuted: '#6b7280',
      border: '#d1d5db',
    },
    trend: { up: '', down: '', stable: '' },
    spacing: { xs: '', sm: '', md: '', lg: '', xl: '' },
    typography: {
      fontFamily: 'Inter',
      headingWeight: 600,
      bodyWeight: 400,
      monoFontFamily: 'Inter',
    },
    shadows: { soft: 'none', medium: 'none' },
  }

  return {
    useThemeTokens: () => tokens,
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
