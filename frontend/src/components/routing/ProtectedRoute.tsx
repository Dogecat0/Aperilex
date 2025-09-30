import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { FullScreenSpinner } from './FullScreenSpinner'

export function ProtectedRoute() {
  const { status, isAuthenticated } = useAuth()
  const location = useLocation()

  const isLoading = status === 'initializing' || status === 'authenticating'

  if (isLoading) {
    return <FullScreenSpinner />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default ProtectedRoute
