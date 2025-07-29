import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { RouterProvider } from 'react-router-dom'
import { queryClient } from '@/lib/query-client'
import { router } from '@/router'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />

      {import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  )
}

export default App
