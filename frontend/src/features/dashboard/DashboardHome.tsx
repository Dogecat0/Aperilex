import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { RecentAnalyses } from './RecentAnalyses'
import { Info } from 'lucide-react'
// import { SystemHealth } from './SystemHealth'

export function DashboardHome() {
  const { setBreadcrumbs } = useAppStore()
  const navigate = useNavigate()

  // Set breadcrumbs on mount
  React.useEffect(() => {
    setBreadcrumbs([{ label: 'Dashboard', isActive: true }])
  }, [setBreadcrumbs])

  const handleViewFilings = () => {
    navigate('/filings')
  }

  const handleSearchCompanies = () => {
    navigate('/companies')
  }

  const handleFindAnalysis = () => {
    navigate('/analyses')
  }

  return (
    <div className="space-y-8">
      {/* S&P 500 Notice */}
      <div className="rounded-lg border bg-blue-50 border-blue-200 p-4">
        <div className="flex items-start space-x-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900">
              Only S&P 500 companies are currently available
            </p>
            <p className="text-sm text-blue-700 mt-1">
              We're currently providing comprehensive analysis for S&P 500 companies for demo purpose.
              More companies will be added in future updates.
            </p>
          </div>
        </div>
      </div>
      {/* Hero Section */}
      <div className="text-center space-y-4 py-12 bg-gradient-to-b from-primary/5 to-background rounded-lg border">
        <h1 className="text-4xl md:text-5xl font-bold text-foreground">Welcome to Aperilex</h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto px-4">
          Your open-source platform for SEC filing analysis and financial insights. Analyze filings,
          discover company data, and generate comprehensive financial reports.
        </p>
        <div className="pt-4">
          <Button size="lg" onClick={handleViewFilings}>
            Get Started
          </Button>
        </div>
      </div>

      {/* View Filings Section */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">View SEC Filings</h2>
            <p className="text-sm text-muted-foreground">
              Browse and analyze SEC filings from public companies
            </p>
          </div>
          <Button onClick={handleViewFilings}>
            <svg className="w-4 h-4 mr-1 sm:mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span className="hidden sm:inline">View Filings</span>
            <span className="sm:hidden">View</span>
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          Access the latest 10-K, 10-Q from public companies.
        </div>
      </div>

      {/* Search Companies Section */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">Search Companies</h2>
            <p className="text-sm text-muted-foreground">
              Find and explore public company information
            </p>
          </div>
          <Button variant="outline" onClick={handleSearchCompanies}>
            <svg className="w-4 h-4 mr-1 sm:mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <span className="hidden sm:inline">Search Companies</span>
            <span className="sm:hidden">Search</span>
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          Search by company name, ticker symbol, or CIK to access detailed company profiles and
          filing history.
        </div>
      </div>

      {/* Find Analysis Section */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">Find Analysis</h2>
            <p className="text-sm text-muted-foreground">Discover existing analyses and insights</p>
          </div>
          <Button variant="outline" onClick={handleFindAnalysis}>
            <svg className="w-4 h-4 mr-1 sm:mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <span className="hidden sm:inline">Find Analysis</span>
            <span className="sm:hidden">Find</span>
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          Browse through comprehensive financial analyses and reports generated from SEC filings.
        </div>
      </div>
    </div>
  )
}
