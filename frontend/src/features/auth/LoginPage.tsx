import type { Location } from 'react-router-dom'
import { Navigate, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { authCopy } from '@/copy/auth'

export function LoginPage() {
  const { status, isAuthenticated, loginWithGoogle, lastError } = useAuth()
  const location = useLocation()

  const fromState = location.state as { from?: Location } | null
  const redirectPath = useMemo(() => {
    const from = fromState?.from
    if (!from) {
      return undefined
    }

    const path = `${from.pathname ?? ''}${from.search ?? ''}${from.hash ?? ''}`
    return path.trim() ? path : undefined
  }, [fromState])

  const isAuthenticating = status === 'authenticating' || status === 'initializing'

  if (isAuthenticated && status === 'authenticated') {
    return <Navigate to={redirectPath ?? '/dashboard'} replace />
  }

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-6 px-6 text-center"
      style={{ background: 'var(--colors-background)', color: 'var(--colors-foreground)' }}
    >
      <div className="space-y-3 max-w-md">
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Stage 5 Authentication
        </p>
        <h1 className="text-3xl font-semibold">Sign in to continue</h1>
        <p className="text-sm text-[var(--colors-foregroundMuted)]">
          Access the dashboard, Learning Hub, and saved analyses by connecting your Google account.
        </p>
      </div>

      <button
        type="button"
        onClick={() => loginWithGoogle(redirectPath)}
        disabled={isAuthenticating}
        className="rounded-full bg-[var(--sentiment-neutral)] px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition-opacity disabled:opacity-60"
      >
        {isAuthenticating ? authCopy.authenticatingLabel : authCopy.loginCta}
      </button>

      {lastError ? (
        <p className="text-xs" style={{ color: 'var(--sentiment-negative)' }}>
          {lastError}
        </p>
      ) : null}
    </div>
  )
}

export default LoginPage
