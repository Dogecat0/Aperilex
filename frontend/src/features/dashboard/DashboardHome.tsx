import React from 'react'
import { useAppStore } from '@/lib/store'
import { RecentAnalyses } from './RecentAnalyses'
// import { MarketOverview } from './MarketOverview'
import { QuickActions } from './QuickActions'
import { SystemHealth } from './SystemHealth'

export function DashboardHome() {
  const { setBreadcrumbs } = useAppStore()

  // Set breadcrumbs on mount
  React.useEffect(() => {
    setBreadcrumbs([{ label: 'Dashboard', isActive: true }])
  }, [setBreadcrumbs])

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Welcome to Aperilex</h1>
        <p className="text-muted-foreground">
          Your open-source platform for SEC filing analysis and financial insights.
        </p>
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Analyses */}
        <div className="lg:col-span-2">
          <RecentAnalyses />
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* <MarketOverview /> */}
          <SystemHealth />
        </div>
      </div>
    </div>
  )
}
