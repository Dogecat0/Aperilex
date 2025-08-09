import { Button } from '@/components/ui/Button'
import { useNavigate } from 'react-router-dom'

export function QuickActions() {
  const navigate = useNavigate()

  const handleNewAnalysis = () => {
    navigate('/analyses')
  }

  const handleSearchCompanies = () => {
    navigate('/companies')
  }

  const handleImportFiling = () => {
    navigate('/filings')
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Button className="h-auto p-4 flex-col space-y-2" onClick={handleNewAnalysis}>
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <span className="text-sm font-medium">Find Analysis</span>
        </Button>

        <Button
          variant="outline"
          className="h-auto p-4 flex-col space-y-2"
          onClick={handleSearchCompanies}
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span className="text-sm font-medium">Search Companies</span>
        </Button>

        <Button
          variant="outline"
          className="h-auto p-4 flex-col space-y-2"
          onClick={handleImportFiling}
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <span className="text-sm font-medium">View Filings</span>
        </Button>
      </div>
    </div>
  )
}
