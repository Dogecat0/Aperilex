import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardHome } from '@/features/dashboard/DashboardHome'
import { NotFound } from '@/components/layout/NotFound'
import { CompanySearch, CompanyProfile } from '@/features/companies'
import { FilingsList, FilingDetails } from '@/features/filings'
import { AnalysesList, AnalysisDetails } from '@/features/analyses'

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
      // Company routes
      { path: 'companies', element: <CompanySearch /> },
      { path: 'companies/:ticker', element: <CompanyProfile /> },
      // Filing routes
      { path: 'filings', element: <FilingsList /> },
      { path: 'filings/:accessionNumber', element: <FilingDetails /> },
      { path: 'filings/:accessionNumber/analysis', element: <AnalysisDetails /> },
      // Analysis routes
      { path: 'analyses', element: <AnalysesList /> },
      { path: 'analyses/:analysisId', element: <AnalysisDetails /> },
    ],
  },
])
