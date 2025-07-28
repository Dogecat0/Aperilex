import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/query-client'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background text-foreground">
        <header className="border-b">
          <div className="container mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-primary">Aperilex</h1>
            <p className="text-sm text-muted-foreground">Financial Analysis Made Simple</p>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8">
          <div className="rounded-lg border bg-card p-6">
            <h2 className="text-xl font-semibold mb-4">Welcome to Aperilex</h2>
            <p className="text-muted-foreground mb-4">
              The open-source platform for SEC filing analysis.
            </p>
            <div className="space-y-2">
              <p className="text-sm">✅ React 19 with TypeScript configured</p>
              <p className="text-sm">✅ Tailwind CSS with custom design system</p>
              <p className="text-sm">✅ API client with error handling</p>
              <p className="text-sm">✅ State management with Zustand</p>
              <p className="text-sm">✅ Server state with TanStack Query</p>
              <p className="text-sm">✅ Development proxy configured</p>
            </div>
          </div>
        </main>
      </div>

      {import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  )
}

export default App
