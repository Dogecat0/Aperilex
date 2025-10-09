import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, RouterProvider } from 'react-router-dom'
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

interface RenderWithProvidersOptions {
  route?: string
  queryClient?: QueryClient
}

export function renderWithProviders(
  component: ReactElement,
  options: RenderWithProvidersOptions = {}
) {
  const queryClient =
    options.queryClient ??
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
        mutations: {
          retry: false,
        },
      },
    })
  const route = options.route ?? '/'

  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{component}</MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
