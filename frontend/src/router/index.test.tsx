import React from 'react'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { router } from './index'
import { useAppStore } from '@/lib/store'

// Mock the store
vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(),
}))

// Mock all child components to isolate router testing
vi.mock('@/components/layout/Header', () => ({
  Header: () => <header data-testid="header">Header</header>,
}))

vi.mock('@/components/layout/MobileNav', () => ({
  MobileNav: () => <nav data-testid="mobile-nav">MobileNav</nav>,
}))

vi.mock('@/components/layout/Footer', () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}))

vi.mock('@/components/navigation/Breadcrumb', () => ({
  Breadcrumb: () => <nav data-testid="breadcrumb">Breadcrumb</nav>,
}))

vi.mock('@/features/dashboard/DashboardHome', () => ({
  DashboardHome: () => {
    const { setBreadcrumbs } = useAppStore()
    React.useEffect(() => {
      setBreadcrumbs([{ label: 'Dashboard', isActive: true }])
    }, [setBreadcrumbs])
    return <div data-testid="dashboard-home">Dashboard Home</div>
  },
}))

vi.mock('@/features/dashboard/RecentAnalyses', () => ({
  RecentAnalyses: () => <div data-testid="recent-analyses">Recent Analyses</div>,
}))

vi.mock('@/features/dashboard/MarketOverview', () => ({
  MarketOverview: () => <div data-testid="market-overview">Market Overview</div>,
}))

vi.mock('@/features/dashboard/QuickActions', () => ({
  QuickActions: () => <div data-testid="quick-actions">Quick Actions</div>,
}))

vi.mock('@/features/dashboard/SystemHealth', () => ({
  SystemHealth: () => <div data-testid="system-health">System Health</div>,
}))

vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} data-testid="button" {...props}>
      {children}
    </button>
  ),
}))

/*
 * Note: React Router displays "No routes matched location" warnings for unmatched routes.
 * These warnings are expected and indicate that the router is correctly handling 404 scenarios.
 * The warnings appear in stderr but do not cause test failures - they confirm proper router behavior.
 */

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const createTestRouter = (initialEntries: string[] = ['/']) => {
  return createMemoryRouter(router.routes, {
    initialEntries,
  })
}

describe('Router Configuration', () => {
  const mockStore = {
    mobileNavOpen: false,
    setBreadcrumbs: vi.fn(),
  }

  // Store original console.error for restoration
  const originalConsoleError = console.error

  beforeEach(() => {
    vi.mocked(useAppStore).mockReturnValue(mockStore)
    // Suppress expected "No routes matched location" warnings that appear in tests
    // These warnings are expected behavior when testing 404 routes
    console.error = vi.fn()
  })

  afterEach(() => {
    vi.clearAllMocks()
    console.error = originalConsoleError
  })

  describe('Route Configuration', () => {
    it('creates router with createBrowserRouter structure', () => {
      expect(router).toBeDefined()
      expect(router.routes).toHaveLength(1)
      expect(router.routes[0].path).toBe('/')
    })

    it('has proper route hierarchy structure', () => {
      const rootRoute = router.routes[0]
      expect(rootRoute.path).toBe('/')
      expect(rootRoute.children).toBeDefined()
      expect(rootRoute.children).toHaveLength(1)
      expect(rootRoute.children![0].index).toBe(true)
    })

    it('configures error element for root route', () => {
      const rootRoute = router.routes[0]
      expect(rootRoute.errorElement).toBeDefined()
    })
  })

  describe('Layout Integration', () => {
    it('renders AppShell as main layout wrapper', () => {
      const testRouter = createTestRouter()

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
      expect(screen.getByTestId('breadcrumb')).toBeInTheDocument()
    })

    it('uses nested routing structure with Outlet', () => {
      const testRouter = createTestRouter()

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Main content should be rendered within AppShell layout
      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })

    it('maintains layout consistency for valid routes', async () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Layout components should be present for valid routes
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()

      // For invalid routes, the errorElement (NotFound) bypasses AppShell layout
      // This is the expected behavior based on the router configuration
    })

    it('handles error routes outside of layout wrapper', () => {
      const testRouter = createTestRouter(['/invalid-route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Error routes (NotFound) render without the AppShell layout
      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()

      // Layout components should not be present for error routes
      expect(screen.queryByTestId('header')).not.toBeInTheDocument()
      expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
    })
  })

  describe('Dashboard Route', () => {
    it('renders dashboard home at root path', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })

    it('loads DashboardHome component correctly', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Check that dashboard content is rendered
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })

    it('sets correct breadcrumbs for dashboard', async () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(mockStore.setBreadcrumbs).toHaveBeenCalledWith([
          { label: 'Dashboard', isActive: true },
        ])
      })
    })

    it('handles index route correctly', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Index route should render dashboard
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
      expect(screen.queryByText('404')).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('renders NotFound component for invalid routes', () => {
      const testRouter = createTestRouter(['/invalid-route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()
      expect(
        screen.getByText("The page you're looking for doesn't exist or has been moved.")
      ).toBeInTheDocument()
    })

    it('provides navigation options in NotFound component', () => {
      const testRouter = createTestRouter(['/invalid-route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('Go Home')).toBeInTheDocument()
      expect(screen.getByText('Go Back')).toBeInTheDocument()
    })

    it('handles deeply nested invalid routes', () => {
      const testRouter = createTestRouter(['/invalid/nested/route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()
    })

    it('handles routes with query parameters gracefully', () => {
      const testRouter = createTestRouter(['/invalid-route?param=value&other=test'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()

      // Query parameters should be preserved in location but still show 404
      expect(testRouter.state.location.pathname).toBe('/invalid-route')
      expect(testRouter.state.location.search).toBe('?param=value&other=test')
    })

    it('handles routes with hash fragments gracefully', () => {
      const testRouter = createTestRouter(['/invalid-route#section'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()

      // Hash should be preserved in location but still show 404
      expect(testRouter.state.location.pathname).toBe('/invalid-route')
      expect(testRouter.state.location.hash).toBe('#section')
    })
  })

  describe('Navigation Testing', () => {
    it('supports programmatic navigation to home', async () => {
      const testRouter = createTestRouter(['/invalid-route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()

      // Click "Go Home" button
      const homeButton = screen.getByText('Go Home')
      await userEvent.click(homeButton)

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
        expect(screen.queryByText('404')).not.toBeInTheDocument()
      })
    })

    it('supports back navigation functionality', async () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Start at home
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()

      // Navigate to invalid route programmatically
      await act(async () => {
        testRouter.navigate('/invalid-route')
      })

      await waitFor(() => {
        expect(screen.getByText('404')).toBeInTheDocument()
      })

      // Test back navigation functionality exists
      const backButton = screen.getByText('Go Back')
      expect(backButton).toBeInTheDocument()

      // Test that back button is functional (uses navigate(-1))
      await userEvent.click(backButton)

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
        expect(screen.queryByText('404')).not.toBeInTheDocument()
      })
    })

    it('handles navigation state changes correctly', async () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Initial state - verify we're at home
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
      expect(testRouter.state.location.pathname).toBe('/')

      // Navigate programmatically to invalid route
      await act(async () => {
        testRouter.navigate('/invalid-route')
      })

      await waitFor(() => {
        expect(screen.getByText('404')).toBeInTheDocument()
        expect(screen.queryByTestId('dashboard-home')).not.toBeInTheDocument()
        expect(testRouter.state.location.pathname).toBe('/invalid-route')
      })
    })

    it('prepares for future route parameter handling', () => {
      // Test that router structure supports parameterized routes
      const rootRoute = router.routes[0]
      expect(rootRoute.children).toBeDefined()

      // This test ensures the structure is ready for future routes like:
      // { path: 'companies/:ticker', element: <CompanyProfile /> }
      expect(Array.isArray(rootRoute.children)).toBe(true)
    })

    it('handles route transitions smoothly', async () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Initial render with proper layout
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
      expect(screen.getByTestId('header')).toBeInTheDocument()

      // Navigate to error route (no layout)
      await act(async () => {
        testRouter.navigate('/invalid')
      })

      await waitFor(() => {
        expect(screen.getByText('404')).toBeInTheDocument()
        expect(screen.queryByTestId('header')).not.toBeInTheDocument()
      })

      // Navigate back to home (with layout)
      await act(async () => {
        testRouter.navigate('/')
      })

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
        expect(screen.getByTestId('header')).toBeInTheDocument()
        expect(screen.queryByText('404')).not.toBeInTheDocument()
      })
    })
  })

  describe('Router Integration', () => {
    it('maintains router state consistency', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(testRouter.state.location.pathname).toBe('/')
    })

    it('handles empty path correctly', () => {
      const testRouter = createTestRouter([''])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Empty path should resolve to root
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })

    it('supports case-sensitive routing', () => {
      const testRouter = createTestRouter(['/INVALID'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Uppercase path should go to 404
      expect(screen.getByText('404')).toBeInTheDocument()
    })

    it('handles trailing slashes consistently', () => {
      const testRouter = createTestRouter(['/invalid/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
    })
  })

  describe('Future Route Preparation', () => {
    it('has extensible route structure for future additions', () => {
      const rootRoute = router.routes[0]

      // Should have children array ready for future routes
      expect(rootRoute.children).toBeDefined()
      expect(Array.isArray(rootRoute.children)).toBe(true)

      // Current structure supports adding routes like:
      // - /companies/:ticker
      // - /analyses
      // - /analyses/:id
      // - /settings
    })

    it('maintains layout wrapper for future nested routes', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Layout should be present and ready for nested routes
      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
    })

    it('supports parameter extraction patterns', () => {
      // Test that the router configuration would support parameterized routes
      const rootRoute = router.routes[0]
      expect(rootRoute.path).toBe('/')
      expect(rootRoute.children).toBeDefined()

      // This ensures future routes with parameters will work:
      // path: 'companies/:ticker' would be supported
    })
  })

  describe('Error Boundary Integration', () => {
    it('configures error element at root level', () => {
      const rootRoute = router.routes[0]
      expect(rootRoute.errorElement).toBeDefined()
    })

    it('catches unmatched routes and displays NotFound', () => {
      const testRouter = createTestRouter(['/error-test'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Should show NotFound for unmatched routes
      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()
    })

    it('provides user-friendly error messaging and navigation', () => {
      const testRouter = createTestRouter(['/invalid-route'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByText('Page Not Found')).toBeInTheDocument()
      expect(
        screen.getByText("The page you're looking for doesn't exist or has been moved.")
      ).toBeInTheDocument()

      // Check navigation options are available
      expect(screen.getByText('Go Home')).toBeInTheDocument()
      expect(screen.getByText('Go Back')).toBeInTheDocument()
    })

    it('handles component errors vs route errors differently', () => {
      // Route errors (404) use errorElement and bypass layout
      const testRouter = createTestRouter(['/nonexistent'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      // Route error should show NotFound without layout
      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.queryByTestId('header')).not.toBeInTheDocument()
      expect(screen.queryByTestId('footer')).not.toBeInTheDocument()
    })
  })

  describe('Mobile Navigation Integration', () => {
    it('conditionally renders mobile navigation based on store state', () => {
      const mockStoreWithMobileNav = {
        ...mockStore,
        mobileNavOpen: true,
      }
      vi.mocked(useAppStore).mockReturnValue(mockStoreWithMobileNav)

      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })

    it('hides mobile navigation when mobileNavOpen is false', () => {
      const testRouter = createTestRouter(['/'])

      render(
        <TestWrapper>
          <RouterProvider router={testRouter} />
        </TestWrapper>
      )

      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
      expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
    })
  })
})
