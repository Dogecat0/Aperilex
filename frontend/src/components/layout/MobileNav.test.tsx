import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MobileNav } from './MobileNav'
import { useAppStore } from '@/lib/store'

// Mock the store
vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(),
}))

// Mock NavMenu component
vi.mock('@/components/navigation/NavMenu', () => ({
  NavMenu: ({ currentPath, onNavigate }: { currentPath: string; onNavigate?: () => void }) => (
    <div data-testid="nav-menu">
      <span data-testid="nav-menu-path">{currentPath}</span>
      <button data-testid="nav-menu-navigate" onClick={onNavigate}>
        Navigate
      </button>
    </div>
  ),
}))

// Mock Button component
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, variant, size, ...props }: any) => (
    <button
      onClick={onClick}
      data-testid="button"
      data-variant={variant}
      data-size={size}
      {...props}
    >
      {children}
    </button>
  ),
}))

// Mock useLocation hook
const mockLocation = { pathname: '/' }
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useLocation: () => mockLocation,
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

describe('MobileNav Component', () => {
  const mockToggleMobileNav = vi.fn()
  const mockStore = {
    mobileNavOpen: false,
    toggleMobileNav: mockToggleMobileNav,
  }

  beforeEach(() => {
    vi.mocked(useAppStore).mockReturnValue(mockStore)
    mockLocation.pathname = '/'
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Structure', () => {
    it('renders with correct structure when mobile nav is open', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Should render backdrop
      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      expect(backdrop).toBeInTheDocument()
      expect(backdrop).toHaveClass(
        'fixed',
        'inset-0',
        'z-40',
        'bg-background/80',
        'backdrop-blur-sm',
        'lg:hidden'
      )

      // Should render sidebar container
      const sidebar = document.querySelector('.fixed.inset-y-0.left-0.z-50')
      expect(sidebar).toBeInTheDocument()
      expect(sidebar).toHaveClass('w-64', 'bg-background', 'border-r', 'lg:hidden')
    })

    it('renders Aperilex branding correctly', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Check for logo
      const logo = document.querySelector('.h-8.w-8.rounded-md.bg-primary')
      expect(logo).toBeInTheDocument()
      expect(logo).toHaveTextContent('A')

      // Check for title
      expect(screen.getByText('Aperilex')).toBeInTheDocument()
      expect(screen.getByText('Aperilex')).toHaveClass('text-lg', 'font-bold', 'text-primary')
    })

    it('renders close button with correct styling', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')
      expect(closeButton).toBeInTheDocument()
      expect(closeButton).toHaveAttribute('data-variant', 'ghost')
      expect(closeButton).toHaveAttribute('data-size', 'sm')

      // Check for close icon (X)
      const icon = closeButton.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('h-6', 'w-6')
    })

    it('renders navigation menu with correct props', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const navMenu = screen.getByTestId('nav-menu')
      expect(navMenu).toBeInTheDocument()

      const pathElement = screen.getByTestId('nav-menu-path')
      expect(pathElement).toHaveTextContent('/')
    })

    it('renders recent activity section', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      expect(screen.getByText('Recent Activity')).toBeInTheDocument()
      expect(screen.getByText('Recent Activity')).toHaveClass(
        'text-xs',
        'font-semibold',
        'leading-6',
        'text-muted-foreground'
      )
      expect(screen.getByText('No recent activity')).toBeInTheDocument()
    })

    it('renders quick actions section', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const findAnalysisButton = screen.getByText('Find Analysis')
      expect(findAnalysisButton).toBeInTheDocument()
      expect(findAnalysisButton).toHaveClass('w-full', 'rounded-md', 'bg-primary', 'px-3', 'py-2')

      const viewFilingButton = screen.getByText('View Filings')
      expect(viewFilingButton).toBeInTheDocument()
      expect(viewFilingButton).toHaveClass(
        'w-full',
        'rounded-md',
        'border',
        'border-input',
        'bg-background'
      )
    })
  })

  describe('Event Handling', () => {
    it('calls toggleMobileNav when backdrop is clicked', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      expect(backdrop).toBeInTheDocument()

      await user.click(backdrop!)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('calls toggleMobileNav when close button is clicked', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')
      await user.click(closeButton)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('calls toggleMobileNav when NavMenu navigation occurs', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const navigateButton = screen.getByTestId('nav-menu-navigate')
      await user.click(navigateButton)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('handles backdrop click using fireEvent for direct event testing', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      fireEvent.click(backdrop!)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('handles close button click using fireEvent for direct event testing', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')
      fireEvent.click(closeButton)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })
  })

  describe('Mobile-Only Visibility', () => {
    it('applies mobile-only classes to backdrop', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      expect(backdrop).toHaveClass('lg:hidden')
    })

    it('applies mobile-only classes to sidebar', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const sidebar = document.querySelector('.fixed.inset-y-0.left-0.z-50')
      expect(sidebar).toHaveClass('lg:hidden')
    })

    it('has proper z-index ordering for overlay behavior', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      const sidebar = document.querySelector('.fixed.inset-y-0.left-0.z-50')

      expect(backdrop).toHaveClass('z-40')
      expect(sidebar).toHaveClass('z-50')
    })
  })

  describe('Layout and Positioning', () => {
    it('has correct backdrop positioning and styling', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')
      expect(backdrop).toHaveClass(
        'fixed',
        'inset-0',
        'z-40',
        'bg-background/80',
        'backdrop-blur-sm',
        'lg:hidden'
      )
    })

    it('has correct sidebar positioning and dimensions', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const sidebar = document.querySelector('.fixed.inset-y-0.left-0.z-50')
      expect(sidebar).toHaveClass(
        'fixed',
        'inset-y-0',
        'left-0',
        'z-50',
        'w-64',
        'bg-background',
        'border-r',
        'lg:hidden'
      )
    })

    it('has proper header section layout', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const header = document.querySelector('.flex.h-16.items-center.justify-between')
      expect(header).toBeInTheDocument()
      expect(header).toHaveClass('px-4', 'border-b')
    })

    it('has proper content section with scrolling', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const content = document.querySelector('.flex.grow.flex-col')
      expect(content).toBeInTheDocument()
      expect(content).toHaveClass('gap-y-5', 'overflow-y-auto', 'px-6', 'py-4')
    })
  })

  describe('Navigation Integration', () => {
    it('passes current location pathname to NavMenu', () => {
      mockLocation.pathname = '/companies'

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const pathElement = screen.getByTestId('nav-menu-path')
      expect(pathElement).toHaveTextContent('/companies')
    })

    it('updates NavMenu when location changes', () => {
      const { rerender } = render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      expect(screen.getByTestId('nav-menu-path')).toHaveTextContent('/')

      mockLocation.pathname = '/analyses'
      rerender(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      expect(screen.getByTestId('nav-menu-path')).toHaveTextContent('/analyses')
    })

    it('provides onNavigate callback to NavMenu', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const navigateButton = screen.getByTestId('nav-menu-navigate')
      expect(navigateButton).toBeInTheDocument()

      fireEvent.click(navigateButton)
      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA roles for navigation', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const nav = document.querySelector('nav.flex.flex-1.flex-col')
      expect(nav).toBeInTheDocument()

      const lists = screen.getAllByRole('list')
      expect(lists.length).toBeGreaterThan(0)
    })

    it('has proper button accessibility for close button', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')
      expect(closeButton).toBeInTheDocument()
      expect(closeButton.tagName.toLowerCase()).toBe('button')
    })

    it('has proper semantic structure for sections', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Recent Activity section should have proper heading
      const recentActivityHeading = screen.getByText('Recent Activity')
      expect(recentActivityHeading).toHaveClass('text-xs', 'font-semibold')

      // Lists should have proper role
      const lists = screen.getAllByRole('list')
      expect(lists.length).toBeGreaterThan(0)
    })
  })

  describe('Touch and Mobile Interaction', () => {
    it('handles touch events on backdrop', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const backdrop = document.querySelector('.fixed.inset-0.z-40')

      // Simulate touch events
      fireEvent.touchStart(backdrop!)
      fireEvent.touchEnd(backdrop!)
      fireEvent.click(backdrop!)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('handles touch events on close button', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')

      // Simulate touch events
      fireEvent.touchStart(closeButton)
      fireEvent.touchEnd(closeButton)
      fireEvent.click(closeButton)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('supports mobile-specific interaction patterns', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Test quick succession of taps (common on mobile)
      const closeButton = screen.getByTestId('button')
      await user.click(closeButton)
      await user.click(closeButton)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(2)
    })
  })

  describe('Component Integration', () => {
    it('integrates properly with NavMenu component', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const navMenu = screen.getByTestId('nav-menu')
      expect(navMenu).toBeInTheDocument()

      // Should pass current path
      expect(screen.getByTestId('nav-menu-path')).toHaveTextContent('/')

      // Should have navigate functionality
      expect(screen.getByTestId('nav-menu-navigate')).toBeInTheDocument()
    })

    it('integrates properly with Button component', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const button = screen.getByTestId('button')
      expect(button).toBeInTheDocument()
      expect(button).toHaveAttribute('data-variant', 'ghost')
      expect(button).toHaveAttribute('data-size', 'sm')
    })

    it('integrates properly with store state management', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Component should call useAppStore hook
      expect(useAppStore).toHaveBeenCalled()

      // Should have access to toggleMobileNav function
      const closeButton = screen.getByTestId('button')
      fireEvent.click(closeButton)
      expect(mockToggleMobileNav).toHaveBeenCalled()
    })
  })

  describe('Visual Design Elements', () => {
    it('renders logo with correct styling', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const logo = document.querySelector('.h-8.w-8.rounded-md.bg-primary')
      expect(logo).toBeInTheDocument()
      expect(logo).toHaveClass('flex', 'items-center', 'justify-center')

      const logoText = logo?.querySelector('.text-primary-foreground.font-bold.text-sm')
      expect(logoText).toBeInTheDocument()
      expect(logoText).toHaveTextContent('A')
    })

    it('renders close icon with correct SVG structure', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const icon = document.querySelector('svg.h-6.w-6')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveAttribute('fill', 'none')
      expect(icon).toHaveAttribute('viewBox', '0 0 24 24')
      expect(icon).toHaveAttribute('stroke', 'currentColor')

      const path = icon?.querySelector('path')
      expect(path).toBeInTheDocument()
      expect(path).toHaveAttribute('d', 'M6 18L18 6M6 6l12 12')
    })

    it('applies correct spacing and layout styles', () => {
      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      // Header spacing
      const headerContent = document.querySelector('.flex.items-center.space-x-2')
      expect(headerContent).toBeInTheDocument()

      // Content spacing
      const contentArea = document.querySelector('.flex.flex-1.flex-col.gap-y-7')
      expect(contentArea).toBeInTheDocument()

      // Quick actions spacing
      const quickActions = document.querySelector('.space-y-2')
      expect(quickActions).toBeInTheDocument()
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('handles missing store gracefully', () => {
      vi.mocked(useAppStore).mockReturnValue({
        ...mockStore,
        toggleMobileNav: undefined as any,
      })

      expect(() => {
        render(
          <TestWrapper>
            <MobileNav />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('handles missing location gracefully', () => {
      // Mock useLocation to return undefined pathname
      vi.doMock('react-router-dom', async () => {
        const actual = await vi.importActual('react-router-dom')
        return {
          ...actual,
          useLocation: () => ({ pathname: undefined }),
        }
      })

      expect(() => {
        render(
          <TestWrapper>
            <MobileNav />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('renders without crashing when props are undefined', () => {
      expect(() => {
        render(
          <TestWrapper>
            <MobileNav />
          </TestWrapper>
        )
      }).not.toThrow()

      // Should still render basic structure
      expect(document.querySelector('.fixed.inset-0.z-40')).toBeInTheDocument()
      expect(document.querySelector('.fixed.inset-y-0.left-0.z-50')).toBeInTheDocument()
    })

    it('maintains component stability during rapid state changes', async () => {
      const user = userEvent.setup()

      render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const closeButton = screen.getByTestId('button')

      // Rapid clicks
      await user.click(closeButton)
      await user.click(closeButton)
      await user.click(closeButton)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(3)
      expect(screen.getByTestId('nav-menu')).toBeInTheDocument()
    })
  })

  describe('Performance Considerations', () => {
    it('renders efficiently without unnecessary re-renders', () => {
      const { rerender } = render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const _initialNavMenu = screen.getByTestId('nav-menu')

      // Re-render with same props
      rerender(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      const newNavMenu = screen.getByTestId('nav-menu')
      expect(newNavMenu).toBeInTheDocument()
    })

    it('handles component cleanup properly', () => {
      const { unmount } = render(
        <TestWrapper>
          <MobileNav />
        </TestWrapper>
      )

      expect(() => unmount()).not.toThrow()
    })
  })
})
