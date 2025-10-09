import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useAuthStore, type AuthSession, type AuthStatus } from '@/state/authStore'
import {
  applyAuthSession,
  parseAuthResponse,
  requestAuthRefresh,
  resolveAuthEndpoint,
  type AuthApiError,
} from '@/state/authSession'

const AUTH_CHANNEL = 'aperilex-auth'
const REFRESH_LEEWAY_MS = 60_000
const MIN_REFRESH_DELAY_MS = 15_000

type AuthChannelMessage =
  | { type: 'logout'; source?: string }
  | { type: 'session-updated'; source: string }

interface GoogleCallbackPayload {
  code: string
  state: string
  redirectUri?: string
}

interface CompleteCallbackResult {
  redirectTo: string | null
}

type BroadcastListener = (event: MessageEvent<AuthChannelMessage>) => void

interface AuthBroadcastChannel {
  postMessage: (message: AuthChannelMessage) => void
  addEventListener: (type: 'message', listener: BroadcastListener) => void
  removeEventListener: (type: 'message', listener: BroadcastListener) => void
  close: () => void
}

const fallbackEmitter = typeof window !== 'undefined' ? new EventTarget() : null

function createAuthChannel(): AuthBroadcastChannel | null {
  if (typeof window === 'undefined') {
    return null
  }

  if ('BroadcastChannel' in window && typeof window.BroadcastChannel === 'function') {
    try {
      return new window.BroadcastChannel(AUTH_CHANNEL)
    } catch (error) {
      console.warn('Failed to create BroadcastChannel, falling back to in-memory channel', error)
    }
  }

  if (!fallbackEmitter) {
    return null
  }

  return {
    postMessage: (message: AuthChannelMessage) => {
      const event = new MessageEvent<AuthChannelMessage>('message', { data: message })
      fallbackEmitter.dispatchEvent(event)
    },
    addEventListener: (_type, listener) => {
      fallbackEmitter.addEventListener('message', listener as EventListener)
    },
    removeEventListener: (_type, listener) => {
      fallbackEmitter.removeEventListener('message', listener as EventListener)
    },
    close: () => {},
  }
}

let hydrationRequested = false
let tabClientId: string | null = null

function createClientId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    try {
      return crypto.randomUUID()
    } catch {
      // Safari private mode can throw; fall back to Math.random variant.
    }
  }

  return `auth-${Math.random().toString(36).slice(2)}`
}

function getTabClientId(): string {
  if (tabClientId === null) {
    tabClientId = createClientId()
  }

  return tabClientId
}

interface RefreshOptions {
  broadcast?: boolean
}

export function useAuth() {
  const status = useAuthStore((state) => state.status)
  const session = useAuthStore((state) => state.session)
  const accessToken = useAuthStore((state) => state.accessToken)
  const accessTokenExpiresAt = useAuthStore((state) => state.accessTokenExpiresAt)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const lastError = useAuthStore((state) => state.lastError)

  const setAuthenticating = useAuthStore((state) => state.setAuthenticating)
  const clearSession = useAuthStore((state) => state.clearSession)
  const setError = useAuthStore((state) => state.setError)

  const refreshTimeoutRef = useRef<number | null>(null)
  const refreshInFlight = useRef<Promise<void> | null>(null)
  const channelRef = useRef<AuthBroadcastChannel | null>(null)
  const clientIdRef = useRef<string | null>(null)
  const callbackTasksRef = useRef<Map<string, Promise<CompleteCallbackResult>>>(new Map())

  if (clientIdRef.current === null) {
    clientIdRef.current = getTabClientId()
  }

  const clientId = clientIdRef.current

  const scheduleRefresh = useCallback((expiresAt: number | null, onRefresh: () => void) => {
    if (typeof window === 'undefined') {
      return
    }

    if (refreshTimeoutRef.current !== null) {
      window.clearTimeout(refreshTimeoutRef.current)
      refreshTimeoutRef.current = null
    }

    if (!expiresAt) {
      return
    }

    const now = Date.now()
    const refreshIn = Math.max(expiresAt - now - REFRESH_LEEWAY_MS, MIN_REFRESH_DELAY_MS)

    if (refreshIn <= 0) {
      if (typeof queueMicrotask === 'function') {
        queueMicrotask(onRefresh)
      } else {
        onRefresh()
      }
      return
    }

    refreshTimeoutRef.current = window.setTimeout(() => {
      refreshTimeoutRef.current = null
      onRefresh()
    }, refreshIn)
  }, [])

  const refreshSession = useCallback(
    async (options: RefreshOptions = {}) => {
      if (refreshInFlight.current) {
        return refreshInFlight.current
      }

      const shouldBroadcast = options.broadcast ?? true

      const task = (async () => {
        try {
          const payload = await requestAuthRefresh()
          const { accessTokenExpiresAt: expiresAt } = applyAuthSession(payload)
          setError(null)
          scheduleRefresh(expiresAt, () => {
            void refreshSession().catch(() => undefined)
          })
          if (shouldBroadcast) {
            channelRef.current?.postMessage({ type: 'session-updated', source: clientId })
          }
        } catch (error) {
          const authError = error as AuthApiError
          if (authError.status === 401) {
            setError(null)
          } else {
            setError(authError.message)
          }
          clearSession()
          if (shouldBroadcast) {
            channelRef.current?.postMessage({ type: 'logout', source: clientId })
          }
          throw error
        }
      })()

      refreshInFlight.current = task
      try {
        await task
      } finally {
        refreshInFlight.current = null
      }
    },
    [clientId, clearSession, scheduleRefresh, setError]
  )

  const completeCallback = useCallback(
    (payload: GoogleCallbackPayload): Promise<CompleteCallbackResult> => {
      const key = `${payload.state}:${payload.code}`
      const existing = callbackTasksRef.current.get(key)
      if (existing) {
        return existing
      }

      setAuthenticating()
      setError(null)

      const task = (async () => {
        try {
          const response = await fetch(resolveAuthEndpoint('/api/auth/google/callback'), {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              code: payload.code,
              state: payload.state,
              redirectUri: payload.redirectUri,
            }),
          })

          const authPayload = await parseAuthResponse(response)
          const { accessTokenExpiresAt: expiresAt } = applyAuthSession(authPayload)
          scheduleRefresh(expiresAt, () => {
            void refreshSession().catch(() => undefined)
          })
          channelRef.current?.postMessage({ type: 'session-updated', source: clientId })

          return { redirectTo: authPayload.redirectTo }
        } catch (error) {
          if (error instanceof Error) {
            const authError = error as AuthApiError
            const message = authError.message || 'Failed to complete authentication flow'
            setError(message)

            if (authError.name !== 'AbortError') {
              const currentState = useAuthStore.getState()
              if (!currentState.session) {
                clearSession()
              }
            }
          } else {
            setError('Failed to complete authentication flow')
            clearSession()
          }

          throw error
        } finally {
          callbackTasksRef.current.delete(key)
        }
      })()

      callbackTasksRef.current.set(key, task)
      return task
    },
    [clientId, clearSession, refreshSession, scheduleRefresh, setAuthenticating, setError]
  )

  const loginWithGoogle = useCallback((redirectTo?: string) => {
    if (typeof window === 'undefined') {
      return
    }

    const search = redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''
    window.location.assign(`/api/auth/google/login${search}`)
  }, [])

  const logout = useCallback(async () => {
    setError(null)

    try {
      await fetch(resolveAuthEndpoint('/api/auth/logout'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
    } catch (error) {
      console.warn('Failed to revoke session', error)
    } finally {
      clearSession()
      channelRef.current?.postMessage({ type: 'logout', source: clientId })
    }
  }, [clearSession, clientId, setError])

  const requireSession = useCallback((): AuthSession => {
    const currentSession = useAuthStore.getState().session
    if (!currentSession) {
      throw new Error('Authentication required')
    }
    return currentSession
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    const channel = createAuthChannel()
    if (!channel) {
      return undefined
    }

    channelRef.current = channel

    const handler: BroadcastListener = (event) => {
      if (!event?.data) {
        return
      }

      if (event.data.type === 'logout') {
        if (event.data.source === clientId) {
          return
        }
        clearSession()
        setError(null)
        return
      }

      if (event.data.type === 'session-updated') {
        if (event.data.source === clientId) {
          return
        }
        void refreshSession({ broadcast: false }).catch(() => undefined)
      }
    }

    channel.addEventListener('message', handler)

    return () => {
      channel.removeEventListener('message', handler)
      channel.close()
      if (channelRef.current === channel) {
        channelRef.current = null
      }
    }
  }, [clientId, clearSession, refreshSession, setError])

  useEffect(() => {
    if (!isAuthenticated) {
      if (refreshTimeoutRef.current !== null && typeof window !== 'undefined') {
        window.clearTimeout(refreshTimeoutRef.current)
        refreshTimeoutRef.current = null
      }
      return
    }

    scheduleRefresh(accessTokenExpiresAt, () => {
      void refreshSession().catch(() => undefined)
    })

    return () => {
      if (refreshTimeoutRef.current !== null && typeof window !== 'undefined') {
        window.clearTimeout(refreshTimeoutRef.current)
        refreshTimeoutRef.current = null
      }
    }
  }, [accessTokenExpiresAt, isAuthenticated, refreshSession, scheduleRefresh])

  useEffect(() => {
    if (typeof document === 'undefined') {
      return
    }

    const handler = () => {
      if (document.visibilityState !== 'visible') {
        return
      }

      if (!accessTokenExpiresAt) {
        return
      }

      const timeUntilExpiry = accessTokenExpiresAt - Date.now()
      if (timeUntilExpiry <= REFRESH_LEEWAY_MS) {
        void refreshSession().catch(() => undefined)
      }
    }

    document.addEventListener('visibilitychange', handler)

    return () => {
      document.removeEventListener('visibilitychange', handler)
    }
  }, [accessTokenExpiresAt, refreshSession])

  useEffect(() => {
    if (status !== 'initializing' || hydrationRequested) {
      return
    }

    hydrationRequested = true

    void refreshSession().catch(() => {
      // Refresh failures during hydration fall back to unauthenticated state.
      clearSession()
    })
  }, [clearSession, refreshSession, status])

  const derivedStatus: AuthStatus = useMemo(() => {
    if (status === 'authenticated' && !session) {
      return 'unauthenticated'
    }
    return status
  }, [session, status])

  return {
    status: derivedStatus,
    session,
    accessToken,
    accessTokenExpiresAt,
    isAuthenticated,
    lastError,
    loginWithGoogle,
    completeCallback,
    logout,
    refreshSession,
    requireSession,
  }
}

export function getAccessTokenSnapshot() {
  return useAuthStore.getState().accessToken
}

export function __resetAuthHydrationForTests() {
  hydrationRequested = false
  tabClientId = null
}
