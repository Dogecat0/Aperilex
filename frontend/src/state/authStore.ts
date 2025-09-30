import { create } from 'zustand'

export type AuthStatus = 'initializing' | 'authenticating' | 'authenticated' | 'unauthenticated'

export interface SessionUser {
  id: string
  email: string
  tier: string | null
  permissions: string[]
}

export interface AuthSession {
  user: SessionUser
  issuedAt: number | null
  refreshExpiresAt: number | null
}

interface AuthStateSlice {
  status: AuthStatus
  session: AuthSession | null
  accessToken: string | null
  accessTokenExpiresAt: number | null
  isAuthenticated: boolean
  lastError: string | null
}

export interface AuthState extends AuthStateSlice {
  setAuthenticating: () => void
  setSession: (payload: {
    session: AuthSession
    accessToken: string
    accessTokenExpiresAt: number | null
  }) => void
  clearSession: () => void
  setAccessToken: (accessToken: string | null, expiresAt: number | null) => void
  setError: (message: string | null) => void
}

const defaultSlice: AuthStateSlice = {
  status: 'initializing',
  session: null,
  accessToken: null,
  accessTokenExpiresAt: null,
  isAuthenticated: false,
  lastError: null,
}

export const useAuthStore = create<AuthState>()((set) => ({
  ...defaultSlice,

  setAuthenticating: () =>
    set((state) => ({
      ...state,
      status: 'authenticating',
      isAuthenticated: false,
      lastError: null,
    })),

  setSession: ({ session, accessToken, accessTokenExpiresAt }) =>
    set((state) => ({
      ...state,
      status: 'authenticated',
      session,
      accessToken,
      accessTokenExpiresAt,
      isAuthenticated: true,
      lastError: null,
    })),

  clearSession: () =>
    set((state) => ({
      ...state,
      ...defaultSlice,
      status: 'unauthenticated',
    })),

  setAccessToken: (accessToken, expiresAt) =>
    set((state) => {
      if (!accessToken) {
        return {
          ...state,
          ...defaultSlice,
          status: 'unauthenticated',
        }
      }

      return {
        ...state,
        accessToken,
        accessTokenExpiresAt: expiresAt,
        status: 'authenticated',
        isAuthenticated: true,
      }
    }),

  setError: (message) =>
    set((state) => ({
      ...state,
      lastError: message,
    })),
}))

export function resetAuthStoreState() {
  useAuthStore.setState((state) => ({
    ...state,
    ...defaultSlice,
  }))
}
