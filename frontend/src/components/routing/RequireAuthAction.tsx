import type { ReactNode, SyntheticEvent } from 'react'
import { useCallback, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

interface RequireAuthActionProps {
  onAuthed: () => void | Promise<void>
  onPromptLogin?: () => void
  redirectTo?: string
  disabled?: boolean
  busy?: boolean
  children: (props: {
    onAction: (event: SyntheticEvent) => void
    disabled: boolean
    isAuthenticated: boolean
    isAuthenticating: boolean
  }) => ReactNode
}

function buildRedirectPath(explicit: string | undefined, locationPath: string): string | undefined {
  const target = explicit ?? locationPath
  const trimmed = target?.trim()
  return trimmed && trimmed.length > 0 ? trimmed : undefined
}

export function RequireAuthAction({
  onAuthed,
  onPromptLogin,
  redirectTo,
  disabled = false,
  busy = false,
  children,
}: RequireAuthActionProps) {
  const { status, isAuthenticated, loginWithGoogle } = useAuth()
  const location = useLocation()

  const isAuthenticating = status === 'authenticating' || status === 'initializing'
  const computedDisabled = disabled || busy

  const redirectTarget = useMemo(() => {
    const currentPath = `${location.pathname}${location.search}${location.hash}`
    return buildRedirectPath(redirectTo, currentPath)
  }, [location.hash, location.pathname, location.search, redirectTo])

  const handlePromptLogin = useCallback(() => {
    if (onPromptLogin) {
      onPromptLogin()
      return
    }

    loginWithGoogle(redirectTarget)
  }, [loginWithGoogle, onPromptLogin, redirectTarget])

  const handleAction = useCallback(
    (event: SyntheticEvent) => {
      if (computedDisabled) {
        event.preventDefault()
        event.stopPropagation()
        return
      }

      if (isAuthenticated) {
        onAuthed()
        return
      }

      if (isAuthenticating) {
        event.preventDefault()
        event.stopPropagation()
        return
      }

      event.preventDefault()
      event.stopPropagation()
      handlePromptLogin()
    },
    [computedDisabled, handlePromptLogin, isAuthenticated, isAuthenticating, onAuthed]
  )

  return (
    <>
      {children({
        onAction: handleAction,
        disabled: computedDisabled || isAuthenticating,
        isAuthenticated,
        isAuthenticating,
      })}
    </>
  )
}

export default RequireAuthAction
