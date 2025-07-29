import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardHome } from '@/features/dashboard/DashboardHome'
import { NotFound } from '@/components/layout/NotFound'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    errorElement: <NotFound />,
    children: [
      {
        index: true,
        element: <DashboardHome />,
      },
      // Future routes will be added here
      // { path: 'companies/:ticker', element: <CompanyProfile /> },
      // { path: 'analyses', element: <AnalysesList /> },
      // { path: 'analyses/:id', element: <AnalysisDetails /> },
      // { path: 'settings', element: <Settings /> },
    ],
  },
])
