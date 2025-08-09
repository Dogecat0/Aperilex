import { useQuery } from '@tanstack/react-query'
import { aperilexApi } from '@/api'

export function Footer() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => aperilexApi.health.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
  })

  return (
    <footer className="border-t bg-background">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col sm:flex-row justify-between items-center space-y-2 sm:space-y-0">
          {/* Left side: Branding */}
          <div className="flex items-center space-x-4">
            <p className="text-sm text-muted-foreground">
              © 2024 Aperilex. Open-source financial analysis platform.
            </p>
          </div>

          {/* Right side: System Status */}
          <div className="flex items-center space-x-4">
            {/* API Status */}
            <div className="flex items-center space-x-1">
              <div
                className={`w-2 h-2 rounded-full ${
                  health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-muted-foreground">
                API {health?.status || 'unknown'}
              </span>
            </div>

            {/* Version */}
            {health?.version && (
              <span className="text-xs text-muted-foreground">v{health.version}</span>
            )}

            {/* Environment Badge */}
            {health?.environment && health.environment !== 'production' && (
              <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">
                {health.environment}
              </span>
            )}
          </div>
        </div>
      </div>
    </footer>
  )
}
