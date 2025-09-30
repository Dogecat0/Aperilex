import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore, resetAuthStoreState, type AuthSession } from './authStore'

describe('authStore', () => {
  beforeEach(() => {
    resetAuthStoreState()
  })

  it('initializes with unauthenticated defaults', () => {
    const state = useAuthStore.getState()
    expect(state.status).toBe('initializing')
    expect(state.isAuthenticated).toBe(false)
    expect(state.session).toBeNull()
    expect(state.accessToken).toBeNull()
  })

  it('promotes session to authenticated state', () => {
    const session: AuthSession = {
      user: {
        id: 'user-123',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: ['analyze:filings'],
      },
      issuedAt: 1700000000000,
      refreshExpiresAt: 1700003600000,
    }

    useAuthStore.getState().setSession({
      session,
      accessToken: 'jwt-token',
      accessTokenExpiresAt: 1700000600000,
    })

    const next = useAuthStore.getState()
    expect(next.status).toBe('authenticated')
    expect(next.isAuthenticated).toBe(true)
    expect(next.session?.user.email).toBe('investor@example.com')
    expect(next.accessToken).toBe('jwt-token')
  })

  it('clears session back to unauthenticated', () => {
    const session: AuthSession = {
      user: {
        id: 'user-123',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: [],
      },
      issuedAt: 1700000000000,
      refreshExpiresAt: 1700003600000,
    }

    useAuthStore.getState().setSession({
      session,
      accessToken: 'jwt-token',
      accessTokenExpiresAt: 1700000600000,
    })

    useAuthStore.getState().clearSession()

    const reset = useAuthStore.getState()
    expect(reset.status).toBe('unauthenticated')
    expect(reset.isAuthenticated).toBe(false)
    expect(reset.session).toBeNull()
    expect(reset.accessToken).toBeNull()
  })

  it('setAccessToken nullifies authentication when token removed', () => {
    const session: AuthSession = {
      user: {
        id: 'user-123',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: [],
      },
      issuedAt: 1700000000000,
      refreshExpiresAt: 1700003600000,
    }

    useAuthStore.getState().setSession({
      session,
      accessToken: 'jwt-token',
      accessTokenExpiresAt: 1700000600000,
    })

    useAuthStore.getState().setAccessToken(null, null)

    const state = useAuthStore.getState()
    expect(state.status).toBe('unauthenticated')
    expect(state.isAuthenticated).toBe(false)
    expect(state.accessToken).toBeNull()
  })
})
