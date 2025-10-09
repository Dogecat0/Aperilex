import { useAuthStore, type AuthSession } from '@/state/authStore'

export interface SessionUserPayload {
  id: string
  email: string
  tier: string | null
  permissions: string[]
}

export interface AuthSessionResponse {
  accessToken: string
  tokenType: string
  expiresIn: number | null
  refreshExpiresIn: number | null
  issuedAt: string | null
  redirectTo: string | null
  user: SessionUserPayload
}

export interface AuthApiError extends Error {
  status?: number
  payload?: unknown
}

const REFRESH_ENDPOINT = '/api/auth/refresh'

let refreshPromise: Promise<AuthSessionResponse> | null = null

export function resolveAuthEndpoint(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  const normalized = path.startsWith('/') ? path : `/${path}`

  if (typeof window !== 'undefined' && typeof window.location !== 'undefined') {
    try {
      return new URL(normalized, window.location.origin).toString()
    } catch {
      // Fall through to localhost fallback.
    }
  }

  return `http://localhost${normalized}`
}

export function computeExpiry(expiresIn: number | null, issuedAt: string | null): number | null {
  if (!expiresIn || expiresIn <= 0) {
    return null
  }

  const issuedTimestamp = issuedAt ? Date.parse(issuedAt) : Number.NaN
  const base = Number.isNaN(issuedTimestamp) ? Date.now() : issuedTimestamp

  return base + expiresIn * 1000
}

export async function parseAuthResponse(response: Response): Promise<AuthSessionResponse> {
  const contentType = response.headers.get('content-type') || ''

  if (response.ok) {
    const payload = await response.json()
    return {
      accessToken: payload.accessToken,
      tokenType: payload.tokenType,
      expiresIn: payload.expiresIn ?? null,
      refreshExpiresIn: payload.refreshExpiresIn ?? null,
      issuedAt: payload.issuedAt ?? null,
      redirectTo: payload.redirectTo ?? null,
      user: {
        id: payload.user?.id ?? '',
        email: payload.user?.email ?? '',
        tier: payload.user?.tier ?? null,
        permissions: Array.isArray(payload.user?.permissions) ? payload.user.permissions : [],
      },
    }
  }

  let payload: unknown

  try {
    payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text()
  } catch {
    payload = null
  }

  const message =
    typeof payload === 'object' && payload !== null && 'message' in payload
      ? String((payload as Record<string, unknown>).message)
      : response.statusText || 'Authentication request failed'

  const authError: AuthApiError = new Error(message)
  authError.status = response.status
  authError.payload = payload

  throw authError
}

export async function requestAuthRefresh(fetchImpl?: typeof fetch): Promise<AuthSessionResponse> {
  if (!refreshPromise) {
    const pending = (async () => {
      const executor = fetchImpl ?? globalThis.fetch
      if (!executor) {
        throw new Error('Fetch API is not available in this environment')
      }

      const response = await executor(resolveAuthEndpoint(REFRESH_ENDPOINT), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      return parseAuthResponse(response)
    })()

    refreshPromise = pending

    pending.finally(() => {
      if (refreshPromise === pending) {
        refreshPromise = null
      }
    })
  }

  return refreshPromise
}

export interface ApplySessionResult {
  accessTokenExpiresAt: number | null
  refreshExpiresAt: number | null
}

export function applyAuthSession(payload: AuthSessionResponse): ApplySessionResult {
  const expiresAt = computeExpiry(payload.expiresIn, payload.issuedAt)
  const refreshExpiresAt = computeExpiry(payload.refreshExpiresIn, payload.issuedAt)
  const issuedAtValue = payload.issuedAt ? Date.parse(payload.issuedAt) : Number.NaN

  const authSession: AuthSession = {
    user: payload.user,
    issuedAt: Number.isNaN(issuedAtValue) ? null : issuedAtValue,
    refreshExpiresAt,
  }

  useAuthStore.getState().setSession({
    session: authSession,
    accessToken: payload.accessToken,
    accessTokenExpiresAt: expiresAt,
  })

  return {
    accessTokenExpiresAt: expiresAt,
    refreshExpiresAt,
  }
}

export function clearAuthSession() {
  useAuthStore.getState().clearSession()
}

export function setAuthError(message: string | null) {
  useAuthStore.getState().setError(message)
}

export function getAccessTokenSnapshot() {
  return useAuthStore.getState().accessToken
}

export function getRefreshExpirySnapshot() {
  return useAuthStore.getState().session?.refreshExpiresAt ?? null
}

export function hasRefreshSession(now: number = Date.now()) {
  const expiry = getRefreshExpirySnapshot()
  if (expiry === null) {
    return false
  }

  return expiry > now
}

export function resetAuthRefreshStateForTests() {
  refreshPromise = null
}
