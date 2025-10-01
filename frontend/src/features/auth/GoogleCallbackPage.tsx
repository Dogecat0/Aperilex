import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { FullScreenSpinner } from '@/components/routing/FullScreenSpinner'
import { useAuth } from '@/hooks/useAuth'
import { clearAuthSession, setAuthError } from '@/state/authSession'

export function GoogleCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { completeCallback } = useAuth()
  const error = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const redirectUri = searchParams.get('redirectUri') ?? undefined

  useEffect(() => {
    if (error) {
      setAuthError(errorDescription ?? 'Google authentication was cancelled')
      clearAuthSession()
      navigate('/login', { replace: true })
      return
    }

    if (!code || !state) {
      setAuthError('Authentication response is missing required parameters')
      clearAuthSession()
      navigate('/login', { replace: true })
      return
    }

    let cancelled = false

    ;(async () => {
      try {
        const { redirectTo } = await completeCallback({ code, state, redirectUri })
        if (!cancelled) {
          navigate(redirectTo ?? '/dashboard', { replace: true })
        }
      } catch (callbackError) {
        if (!cancelled) {
          if (callbackError instanceof Error) {
            setAuthError(callbackError.message)
          } else {
            setAuthError('Failed to complete authentication flow')
          }
          clearAuthSession()
          navigate('/login', { replace: true })
        }
      }
    })().catch(() => {
      // Errors are handled in the try/catch block above; this keeps the
      // async function signature quiet for TypeScript.
    })

    return () => {
      cancelled = true
    }
  }, [code, completeCallback, error, errorDescription, navigate, redirectUri, state])

  return <FullScreenSpinner />
}

export default GoogleCallbackPage
