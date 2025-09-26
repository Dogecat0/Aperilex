import { useQuery } from '@tanstack/react-query'
import { aperilexApi } from '@/api'

export function SystemHealth() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health', 'detailed'],
    queryFn: () => aperilexApi.health.detailed(),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600'
      case 'warning':
        return 'text-yellow-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500'
      case 'warning':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">System Health</h2>

      {isLoading ? (
        <div className="space-y-2">
          <div className="animate-pulse h-4 bg-muted rounded w-3/4"></div>
          <div className="animate-pulse h-4 bg-muted rounded w-1/2"></div>
          <div className="animate-pulse h-4 bg-muted rounded w-2/3"></div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Overall Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Overall Status</span>
            <div className="flex items-center space-x-2">
              <div
                className={`w-2 h-2 rounded-full ${getStatusDot(health?.status || 'unknown')}`}
              />
              <span
                className={`text-sm font-semibold ${getStatusColor(health?.status || 'unknown')}`}
              >
                {health?.status || 'Unknown'}
              </span>
            </div>
          </div>

          <hr />

          {/* Service Status */}
          {health?.services &&
            Object.entries(health.services).map(([service, status]) => {
              // Skip if status is null or invalid
              if (!status || typeof status !== 'object' || !status.status) {
                return null
              }

              return (
                <div key={service} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{service.replace(/_/g, ' ')}</span>
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusDot(status.status)}`} />
                    <span className={`text-xs ${getStatusColor(status.status)}`}>
                      {status.status}
                    </span>
                  </div>
                </div>
              )
            })}

          <hr />

          {/* System Info */}
          <div className="space-y-2 text-xs text-muted-foreground">
            {health?.version && (
              <div className="flex justify-between">
                <span>Version</span>
                <span>{health.version}</span>
              </div>
            )}
            {health?.environment && (
              <div className="flex justify-between">
                <span>Environment</span>
                <span className="capitalize">{health.environment}</span>
              </div>
            )}
            {health?.timestamp && (
              <div className="flex justify-between">
                <span>Last updated</span>
                <span>{new Date(health.timestamp).toLocaleTimeString()}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
