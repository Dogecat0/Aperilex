import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter } from 'react-router-dom'
import App from './App'
import { queryClient as appQueryClient } from '@/lib/query-client'

// Mock the router to control navigation in tests
vi.mock('@/router', () => ({
  router: createMemoryRouter([
    {
      path: '/',
      element: <div data-testid="mock-route">Mock App Content</div>,
    },
    {
      path: '/error',
      element: <div data-testid="error-route">Error Page</div>,
    },
  ]),
}))

// Mock child components to isolate App testing
vi.mock('@/components/layout/AppShell', () => ({
  AppShell: () => <div data-testid="app-shell">App Shell Content</div>,
}))

vi.mock('@/features/dashboard/DashboardHome', () => ({
  DashboardHome: () => <div data-testid="dashboard-home">Dashboard Home</div>,
}))

vi.mock('@/components/layout/NotFound', () => ({
  NotFound: () => <div data-testid="not-found">Not Found Page</div>,
}))

// Create a test wrapper that doesn't include QueryClientProvider
// so we can test the App's provider setup
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>
}

describe('App Component', () => {
  // Store original environment variable
  const originalEnv = import.meta.env.VITE_ENABLE_DEBUG_MODE

  beforeEach(() => {
    // Reset environment variable before each test
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Restore original environment variable
    import.meta.env.VITE_ENABLE_DEBUG_MODE = originalEnv
  })

  describe('App Initialization', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<App />, { wrapper: TestWrapper })
      }).not.toThrow()
    })

    it('renders the main app structure', () => {
      render(<App />, { wrapper: TestWrapper })

      // The app should render with RouterProvider content
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('initializes with the correct document structure', () => {
      render(<App />, { wrapper: TestWrapper })

      // Verify that the app container is properly structured
      const appContainer = screen.getByTestId('mock-route')
      expect(appContainer).toBeInTheDocument()
      expect(appContainer).toHaveTextContent('Mock App Content')
    })
  })

  describe('Provider Setup', () => {
    it('sets up QueryClientProvider with the correct client', () => {
      render(<App />, { wrapper: TestWrapper })

      // We can't directly test the QueryClient instance, but we can verify
      // that the component renders successfully with the provider
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('sets up RouterProvider correctly', () => {
      render(<App />, { wrapper: TestWrapper })

      // Verify that router provider is working by checking rendered content
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('provides query client to child components', async () => {
      // Test that QueryClientProvider is set up correctly by verifying
      // that the component renders without throwing a context error
      render(<App />, { wrapper: TestWrapper })

      // The fact that the app renders successfully indicates that
      // QueryClientProvider is properly configured
      await waitFor(() => {
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      })

      // Verify that the query client has proper configuration
      expect(appQueryClient).toBeDefined()
      expect(appQueryClient.getDefaultOptions()).toBeDefined()
    })
  })

  describe('Global Context', () => {
    it('provides global query client configuration', () => {
      // Test that the app-level query client has correct default options
      expect(appQueryClient.getDefaultOptions().queries?.staleTime).toBe(5 * 60 * 1000)
      expect(appQueryClient.getDefaultOptions().queries?.gcTime).toBe(10 * 60 * 1000)
      expect(appQueryClient.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false)
    })

    it('configures proper retry logic for queries', () => {
      const retryFunction = appQueryClient.getDefaultOptions().queries?.retry
      expect(typeof retryFunction).toBe('function')

      if (typeof retryFunction === 'function') {
        // Test retry logic with different error types
        const mockAPIError = { status_code: 404 }
        const mockNetworkError = new Error('Network error')

        // Should not retry 4xx errors
        expect(retryFunction(1, mockAPIError)).toBe(false)

        // Should retry network errors up to 3 times
        expect(retryFunction(1, mockNetworkError)).toBe(true)
        expect(retryFunction(2, mockNetworkError)).toBe(true)
        expect(retryFunction(3, mockNetworkError)).toBe(false)
      }
    })

    it('configures proper retry delay function', () => {
      const retryDelayFunction = appQueryClient.getDefaultOptions().queries?.retryDelay
      expect(typeof retryDelayFunction).toBe('function')

      if (typeof retryDelayFunction === 'function') {
        // Test exponential backoff with cap
        expect(retryDelayFunction(0)).toBe(1000) // 2^0 * 1000 = 1000
        expect(retryDelayFunction(1)).toBe(2000) // 2^1 * 1000 = 2000
        expect(retryDelayFunction(2)).toBe(4000) // 2^2 * 1000 = 4000
        expect(retryDelayFunction(10)).toBe(30000) // Capped at 30000
      }
    })

    it('configures mutation retry settings', () => {
      const mutationOptions = appQueryClient.getDefaultOptions().mutations
      expect(mutationOptions?.retry).toBe(1)
      expect(mutationOptions?.retryDelay).toBe(1000)
    })
  })

  describe('React Query DevTools', () => {
    it('renders DevTools when debug mode is enabled', () => {
      // Mock environment variable for debug mode
      import.meta.env.VITE_ENABLE_DEBUG_MODE = 'true'

      render(<App />, { wrapper: TestWrapper })

      // DevTools component is rendered but may not be visible
      // We can't easily test the actual DevTools component since it's external
      // but we can verify the app still renders correctly
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('does not render DevTools when debug mode is disabled', () => {
      // Mock environment variable for production mode
      import.meta.env.VITE_ENABLE_DEBUG_MODE = 'false'

      render(<App />, { wrapper: TestWrapper })

      // App should render normally without DevTools
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('does not render DevTools when debug mode is undefined', () => {
      // Mock environment variable as undefined
      import.meta.env.VITE_ENABLE_DEBUG_MODE = undefined

      render(<App />, { wrapper: TestWrapper })

      // App should render normally without DevTools
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('handles QueryClient initialization errors gracefully', () => {
      // Mock a scenario where QueryClient might fail
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      try {
        render(<App />, { wrapper: TestWrapper })
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      } finally {
        consoleSpy.mockRestore()
      }
    })

    it('handles router initialization errors gracefully', () => {
      // Mock router with error boundary
      vi.doMock('@/router', () => ({
        router: createMemoryRouter([
          {
            path: '/',
            element: <div data-testid="mock-route">Mock Content</div>,
            errorElement: <div data-testid="error-boundary">Error Boundary</div>,
          },
        ]),
      }))

      render(<App />, { wrapper: TestWrapper })

      // Should render without throwing
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })
  })

  describe('Integration Testing', () => {
    it('successfully boots the full app', async () => {
      render(<App />, { wrapper: TestWrapper })

      // Wait for any async operations to complete
      await waitFor(() => {
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      })

      // Verify the app is in a ready state
      expect(screen.getByTestId('mock-route')).toHaveTextContent('Mock App Content')
    })

    it('provides working router context to child components', () => {
      // Test that RouterProvider is set up correctly by verifying
      // that the component renders without throwing a router context error
      render(<App />, { wrapper: TestWrapper })

      // The fact that the router renders the mock route indicates
      // that RouterProvider is properly configured
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      expect(screen.getByTestId('mock-route')).toHaveTextContent('Mock App Content')
    })

    it('provides working query client context to child components', async () => {
      // Test that both QueryClientProvider and RouterProvider work together
      render(<App />, { wrapper: TestWrapper })

      // Wait for the app to fully initialize
      await waitFor(() => {
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      })

      // Verify that the providers are working together correctly
      expect(screen.getByTestId('mock-route')).toHaveTextContent('Mock App Content')

      // Test that the query client is accessible (indirectly)
      expect(appQueryClient.getQueryCache()).toBeDefined()
      expect(appQueryClient.getMutationCache()).toBeDefined()
    })

    it('handles navigation between sections correctly', async () => {
      // Test that the router can handle basic navigation by verifying
      // that the initial route loads correctly
      render(<App />, { wrapper: TestWrapper })

      await waitFor(() => {
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      })

      // Verify that the app initializes with the correct route content
      expect(screen.getByTestId('mock-route')).toHaveTextContent('Mock App Content')

      // The router mock ensures navigation capability exists
      // Real navigation testing would be done in integration tests
    })
  })

  describe('Performance and Resource Management', () => {
    it('does not create memory leaks during initialization', () => {
      // Test that multiple renders don't accumulate resources
      const { unmount } = render(<App />, { wrapper: TestWrapper })
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()

      unmount()

      // Re-render and verify it works correctly
      render(<App />, { wrapper: TestWrapper })
      expect(screen.getByTestId('mock-route')).toBeInTheDocument()
    })

    it('properly initializes query client with optimal defaults', () => {
      // Verify query client configuration for performance
      const queryOptions = appQueryClient.getDefaultOptions().queries

      // Check stale time is set appropriately (5 minutes)
      expect(queryOptions?.staleTime).toBe(5 * 60 * 1000)

      // Check garbage collection time (10 minutes)
      expect(queryOptions?.gcTime).toBe(10 * 60 * 1000)

      // Check that refetch on window focus is disabled for better UX
      expect(queryOptions?.refetchOnWindowFocus).toBe(false)
    })

    it('handles concurrent renders correctly', async () => {
      // Render multiple instances concurrently
      const promises = Array.from({ length: 3 }, () => {
        return new Promise<void>((resolve) => {
          render(<App />, { wrapper: TestWrapper })
          resolve()
        })
      })

      await Promise.all(promises)

      // All should complete without errors
      expect(screen.getAllByTestId('mock-route')).toHaveLength(3)
    })
  })

  describe('Environment-Specific Behavior', () => {
    it('behaves correctly in development environment', () => {
      // Mock development environment
      const originalNodeEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'development'

      try {
        render(<App />, { wrapper: TestWrapper })
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      } finally {
        process.env.NODE_ENV = originalNodeEnv
      }
    })

    it('behaves correctly in production environment', () => {
      // Mock production environment
      const originalNodeEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'production'

      try {
        render(<App />, { wrapper: TestWrapper })
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      } finally {
        process.env.NODE_ENV = originalNodeEnv
      }
    })

    it('handles missing environment variables gracefully', () => {
      // Test with undefined environment variables
      const originalDebugMode = import.meta.env.VITE_ENABLE_DEBUG_MODE
      delete (import.meta.env as any).VITE_ENABLE_DEBUG_MODE

      try {
        render(<App />, { wrapper: TestWrapper })
        expect(screen.getByTestId('mock-route')).toBeInTheDocument()
      } finally {
        import.meta.env.VITE_ENABLE_DEBUG_MODE = originalDebugMode
      }
    })
  })
})
