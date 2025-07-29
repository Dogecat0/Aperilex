import { useAnalysisStore } from '@/lib/store'
import { Skeleton } from '@/components/ui/Skeleton'

export function RecentAnalyses() {
  const { recentAnalyses } = useAnalysisStore()

  return (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Recent Analyses</h2>
        <button className="text-sm text-primary hover:text-primary/80">View all</button>
      </div>

      {recentAnalyses.length === 0 ? (
        <div className="space-y-4">
          <div className="text-center py-8">
            <svg
              className="mx-auto h-12 w-12 text-muted-foreground"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-semibold text-foreground">No analyses yet</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Get started by analyzing your first SEC filing.
            </p>
            <div className="mt-6">
              <button className="inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90">
                <svg
                  className="-ml-0.5 mr-1.5 h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
                New Analysis
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Placeholder for when we have real data */}
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      )}
    </div>
  )
}
