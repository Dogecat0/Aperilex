import {
  createBrowserRouter,
  createMemoryRouter,
  Navigate,
  type RouteObject,
} from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/components/routing/ProtectedRoute'
import { DashboardPage } from '@/features/dashboard'
import { FilingDetailPage } from '@/features/filing-detail'
import { LearningHubPage } from '@/features/learning'
import { SavedItemsPage } from '@/features/saved'
import { AnalyzeFilingsPage } from '@/features/filings'
import { LoginPage, GoogleCallbackPage } from '@/features/auth'
import { LandingPage } from '@/features/landing'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: 'dashboard',
            element: <DashboardPage />,
          },
          {
            path: 'analyze',
            element: <AnalyzeFilingsPage />,
          },
          {
            path: 'filing/:id',
            element: <FilingDetailPage />,
          },
          {
            path: 'learn',
            element: <LearningHubPage />,
          },
          {
            path: 'saved',
            element: <SavedItemsPage />,
          },
        ],
      },
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/google/callback',
    element: <GoogleCallbackPage />,
  },
]

export const router = createBrowserRouter(routes)

export function createTestRouter(initialEntries?: string[]) {
  return createMemoryRouter(routes, { initialEntries })
}
