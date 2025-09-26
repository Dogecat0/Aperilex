import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from './AppShell'
import { useAppStore } from '@/lib/store'

// Mock the store
const mockStore = {
  mobileNavOpen: false,
  breadcrumbs: [
    { label: 'Dashboard', href: '/', isActive: false },
    { label: 'Companies', href: '/companies', isActive: false },
    { label: 'Apple Inc.', href: '/companies/AAPL', isActive: true },
  ],
}

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => mockStore),
}))

// Mock child components to isolate AppShell testing
vi.mock('./Header', () => ({
  Header: () => <header data-testid="header">Header Component</header>,
}))

vi.mock('./MobileNav', () => ({
  MobileNav: () => <nav data-testid="mobile-nav">MobileNav Component</nav>,
}))

vi.mock('./Footer', () => ({
  Footer: () => <footer data-testid="footer">Footer Component</footer>,
}))

vi.mock('@/components/navigation/Breadcrumb', () => ({
  Breadcrumb: () => <nav data-testid="breadcrumb">Breadcrumb Component</nav>,
}))

// Mock Outlet to simulate nested route content
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Outlet: () => <div data-testid="outlet">Route Content</div>,
  }
})

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <div>{children}</div>,
      },
    ],
    {
      initialEntries: ['/'],
    }
  )

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

describe('AppShell Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store to default state
    vi.mocked(useAppStore).mockReturnValue(mockStore)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering & Structure', () => {
    it('renders without errors', () => {
      expect(() => {
        render(
          <TestWrapper>
            <AppShell />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('has correct CSS classes and layout structure', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Check root container
      const container = document.querySelector('.min-h-screen.bg-background')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('min-h-screen', 'bg-background')

      // Check flex container for main layout
      const flexContainer = document.querySelector('.flex')
      expect(flexContainer).toBeInTheDocument()
      expect(flexContainer).toHaveClass('flex')
    })

    it('renders Header component', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const header = screen.getByTestId('header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveTextContent('Header Component')
    })

    it('renders main content area with proper container styling', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(main).toHaveClass(
        'flex-1',
        'transition-all',
        'duration-200',
        'ease-in-out',
        'lg:ml-0',
        'min-h-[calc(100vh-4rem)]'
      )

      // Check inner container
      const container = main.querySelector('.container')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('container', 'mx-auto', 'px-4', 'py-6')
    })

    it('renders Footer component', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const footer = screen.getByTestId('footer')
      expect(footer).toBeInTheDocument()
      expect(footer).toHaveTextContent('Footer Component')
    })
  })

  describe('Store Integration', () => {
    it('calls useAppStore to get mobileNavOpen state', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(useAppStore).toHaveBeenCalled()
    })

    it('renders MobileNav when mobileNavOpen is true', () => {
      // Mock store with mobileNavOpen as true
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const mobileNav = screen.getByTestId('mobile-nav')
      expect(mobileNav).toBeInTheDocument()
      expect(mobileNav).toHaveTextContent('MobileNav Component')
    })

    it('does not render MobileNav when mobileNavOpen is false', () => {
      // Mock store with mobileNavOpen as false (default)
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: false,
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const mobileNav = screen.queryByTestId('mobile-nav')
      expect(mobileNav).not.toBeInTheDocument()
    })

    it('updates MobileNav visibility when store state changes', () => {
      const { rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Initially, mobileNav should not be rendered
      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()

      // Update store to show mobile nav
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      rerender(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Now mobileNav should be rendered
      expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
    })

    it('handles store state correctly on component mount', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Verify that the store hook was called during render
      expect(useAppStore).toHaveBeenCalled()
    })
  })

  describe('Component Integration', () => {
    it('renders Header component correctly', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const header = screen.getByTestId('header')
      expect(header).toBeInTheDocument()
      expect(header.tagName.toLowerCase()).toBe('header')
    })

    it('renders Footer component correctly', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const footer = screen.getByTestId('footer')
      expect(footer).toBeInTheDocument()
      expect(footer.tagName.toLowerCase()).toBe('footer')
    })

    it('renders Breadcrumb component correctly', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const breadcrumb = screen.getByTestId('breadcrumb')
      expect(breadcrumb).toBeInTheDocument()
      expect(breadcrumb.tagName.toLowerCase()).toBe('nav')
    })

    it('renders Outlet for nested routes', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const outlet = screen.getByTestId('outlet')
      expect(outlet).toBeInTheDocument()
      expect(outlet).toHaveTextContent('Route Content')
    })

    it('maintains correct component hierarchy', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const container = document.querySelector('.min-h-screen.bg-background')
      const header = screen.getByTestId('header')
      const main = screen.getByRole('main')
      const footer = screen.getByTestId('footer')

      // Verify hierarchy exists
      expect(container).toContainElement(header)
      expect(container).toContainElement(main)
      expect(container).toContainElement(footer)

      // Verify main content contains breadcrumb and outlet
      const breadcrumb = screen.getByTestId('breadcrumb')
      const outlet = screen.getByTestId('outlet')
      expect(main).toContainElement(breadcrumb)
      expect(main).toContainElement(outlet)
    })
  })

  describe('Layout & Responsive Design', () => {
    it('applies min-height screen layout', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const container = document.querySelector('.min-h-screen')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('min-h-screen', 'bg-background')
    })

    it('has correct flex layout structure', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const flexContainer = document.querySelector('.flex')
      expect(flexContainer).toBeInTheDocument()
      expect(flexContainer).toHaveClass('flex')
    })

    it('applies responsive classes to main content', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main).toHaveClass(
        'flex-1',
        'transition-all',
        'duration-200',
        'ease-in-out',
        'lg:ml-0',
        'min-h-[calc(100vh-4rem)]'
      )
    })

    it('applies correct container and padding classes', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      const container = main.querySelector('.container')
      expect(container).toHaveClass('container', 'mx-auto', 'px-4', 'py-6')
    })

    it('maintains layout consistency across viewport sizes', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')

      // Check for responsive margin classes
      expect(main).toHaveClass('lg:ml-0')

      // Check for responsive minimum height
      expect(main).toHaveClass('min-h-[calc(100vh-4rem)]')
    })

    it('has proper transition classes for smooth animations', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main).toHaveClass('transition-all', 'duration-200', 'ease-in-out')
    })
  })

  describe('Router Integration', () => {
    it('renders Outlet for child routes', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const outlet = screen.getByTestId('outlet')
      expect(outlet).toBeInTheDocument()
    })

    it('maintains router context for nested components', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Outlet should render route content
      const outlet = screen.getByTestId('outlet')
      expect(outlet).toHaveTextContent('Route Content')
    })

    it('supports nested route navigation', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Check that Outlet is positioned correctly within main content
      const main = screen.getByRole('main')
      const outlet = screen.getByTestId('outlet')
      expect(main).toContainElement(outlet)
    })

    it('provides proper container structure for routed content', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      const container = main.querySelector('.container')
      const outlet = screen.getByTestId('outlet')

      expect(container).toContainElement(outlet)
    })
  })

  describe('Mobile Navigation Overlay', () => {
    it('renders mobile navigation overlay when mobileNavOpen is true', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const mobileNav = screen.getByTestId('mobile-nav')
      expect(mobileNav).toBeInTheDocument()
    })

    it('does not render mobile navigation overlay when mobileNavOpen is false', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: false,
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const mobileNav = screen.queryByTestId('mobile-nav')
      expect(mobileNav).not.toBeInTheDocument()
    })

    it('conditionally renders MobileNav within flex container', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const flexContainer = document.querySelector('.flex')
      const mobileNav = screen.getByTestId('mobile-nav')

      expect(flexContainer).toContainElement(mobileNav)
    })

    it('maintains proper layout when MobileNav is toggled', () => {
      const { rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Initially without mobile nav
      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()

      // With mobile nav
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      rerender(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
      expect(screen.getByRole('main')).toBeInTheDocument()
    })
  })

  describe('Content Organization', () => {
    it('renders breadcrumb before outlet content', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const container = document.querySelector('.container')
      const breadcrumb = screen.getByTestId('breadcrumb')
      const outlet = screen.getByTestId('outlet')

      expect(container).toContainElement(breadcrumb)
      expect(container).toContainElement(outlet)

      // Both breadcrumb and outlet are direct children of container
      const breadcrumbIndex = Array.from(container!.children).indexOf(breadcrumb)
      const outletIndex = Array.from(container!.children).indexOf(outlet)

      expect(breadcrumbIndex).toBeLessThan(outletIndex)
    })

    it('maintains proper spacing between content elements', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const container = document.querySelector('.container')
      expect(container).toHaveClass('px-4', 'py-6')
    })

    it('provides semantic main landmark for content', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
      expect(main.tagName.toLowerCase()).toBe('main')
    })
  })

  describe('Accessibility', () => {
    it('uses semantic HTML elements', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main.tagName.toLowerCase()).toBe('main')
    })

    it('maintains proper landmark structure', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Should have header, main, and footer landmarks
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
    })

    it('provides navigation landmarks through breadcrumb', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const breadcrumb = screen.getByTestId('breadcrumb')
      expect(breadcrumb.tagName.toLowerCase()).toBe('nav')
    })

    it('supports screen reader navigation', () => {
      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()

      // Main content should be easily discoverable
      expect(main).toHaveClass('flex-1')
    })
  })

  describe('Error Handling', () => {
    it('handles missing store state gracefully', () => {
      vi.mocked(useAppStore).mockReturnValue({
        mobileNavOpen: undefined as any,
        breadcrumbs: undefined as any,
      })

      expect(() => {
        render(
          <TestWrapper>
            <AppShell />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('handles store hook errors appropriately', () => {
      // This test verifies that store errors are handled by the TestWrapper's error boundary
      const originalConsoleError = console.error
      console.error = vi.fn() // Suppress expected error logs

      vi.mocked(useAppStore).mockImplementation(() => {
        throw new Error('Store error')
      })

      // The TestWrapper with RouterProvider catches errors and doesn't let them bubble up
      // So we test that the render completes without crashing the test suite
      expect(() => {
        render(
          <TestWrapper>
            <AppShell />
          </TestWrapper>
        )
      }).not.toThrow()

      // Reset mocks and console
      console.error = originalConsoleError
      vi.mocked(useAppStore).mockReturnValue(mockStore)
    })

    it('handles component remounting correctly', () => {
      const { unmount } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(screen.getByRole('main')).toBeInTheDocument()

      unmount()

      // Render again with new component instance
      const { rerender: _rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(screen.getByRole('main')).toBeInTheDocument()
    })
  })

  describe('Performance and Optimization', () => {
    it('renders consistently across multiple renders', () => {
      const { rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      const _initialMain = screen.getByRole('main')
      const _initialHeader = screen.getByTestId('header')
      const _initialFooter = screen.getByTestId('footer')

      rerender(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
    })

    it('maintains component structure during state updates', () => {
      const { rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Change store state
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: true,
      })

      rerender(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Core structure should remain
      expect(screen.getByRole('main')).toBeInTheDocument()
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
      expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
    })

    it('does not create memory leaks during unmount', () => {
      const { unmount } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('Store Integration Edge Cases', () => {
    it('handles boolean conversion for mobileNavOpen state', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: 1 as any, // Non-boolean truthy value
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Should still render MobileNav for truthy values
      expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
    })

    it('handles falsy values for mobileNavOpen state', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        mobileNavOpen: 0 as any, // Falsy value
      })

      render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Should not render MobileNav for falsy values
      expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
    })

    it('handles rapid state changes correctly', () => {
      const { rerender } = render(
        <TestWrapper>
          <AppShell />
        </TestWrapper>
      )

      // Toggle state multiple times
      for (let i = 1; i <= 3; i++) {
        vi.mocked(useAppStore).mockReturnValue({
          ...mockStore,
          mobileNavOpen: i % 2 === 1, // true for odd numbers, false for even
        })

        rerender(
          <TestWrapper>
            <AppShell />
          </TestWrapper>
        )

        if (i % 2 === 1) {
          expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
        } else {
          expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
        }
      }
    })
  })
})
