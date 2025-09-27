import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from '@/components/ThemeProvider'
import { createTestRouter } from '@/router'

export function renderWithRouter(initialEntries: string[] = ['/']): {
  router: ReturnType<typeof createTestRouter>
} {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

  const router = createTestRouter(initialEntries)

  render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>
  )

  return { router }
}

export function renderWithProviders(component: ReactElement) {
  const queryClient = new QueryClient()

  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
    </ThemeProvider>
  )
}
