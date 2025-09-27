import { createBrowserRouter, createMemoryRouter, Navigate, type RouteObject } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardPage } from '@/features/dashboard'
import { FilingDetailPage } from '@/features/filing-detail'
import { LearningHubPage } from '@/features/learning'
import { SavedItemsPage } from '@/features/saved'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
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
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
]

export const router = createBrowserRouter(routes)

export function createTestRouter(initialEntries?: string[]) {
  return createMemoryRouter(routes, { initialEntries })
}
