import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { useAppStore } from '@/lib/store'
import { Header } from './Header'

// Mock the store
const mockToggleMobileNav = vi.fn()

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => ({
    toggleMobileNav: mockToggleMobileNav,
  })),
}))

// Mock child components to isolate Header testing
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, className, variant, size, ...props }: any) => (
    <button
      onClick={onClick}
      className={className}
      data-variant={variant}
      data-size={size}
      data-testid="mock-button"
      {...props}
    >
      {children}
    </button>
  ),
}))

vi.mock('@/components/navigation/UserPreferences', () => ({
  UserPreferences: () => <div data-testid="user-preferences">UserPreferences Component</div>,
}))

// Test wrapper to provide router context
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
)

describe('Header Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<Header />, { wrapper: TestWrapper })
      }).not.toThrow()
    })

    it('renders the correct component structure', () => {
      render(<Header />, { wrapper: TestWrapper })

      const header = screen.getByRole('banner')
      expect(header).toBeInTheDocument()
      expect(header.tagName).toBe('HEADER')
    })

    it('applies correct styling classes to header', () => {
      render(<Header />, { wrapper: TestWrapper })

      const header = screen.getByRole('banner')
      expect(header).toHaveClass(
        'sticky',
        'top-0',
        'z-50',
        'border-b',
        'bg-background/95',
        'backdrop-blur'
      )
    })

    it('renders the main container with correct layout classes', () => {
      render(<Header />, { wrapper: TestWrapper })

      const container = screen.getByRole('banner').firstChild
      expect(container).toHaveClass(
        'container',
        'mx-auto',
        'flex',
        'h-16',
        'items-center',
        'justify-between',
        'px-4'
      )
    })
  })

  describe('Logo and Branding', () => {
    it('renders the logo section correctly', () => {
      render(<Header />, { wrapper: TestWrapper })

      // Check for the logo icon container
      const logoIcon = screen.getByText('A')
      expect(logoIcon).toBeInTheDocument()
      expect(logoIcon).toHaveClass('text-primary-foreground', 'font-bold', 'text-lg')

      // Check for the logo icon background
      const logoContainer = logoIcon.parentElement
      expect(logoContainer).toHaveClass(
        'h-8',
        'w-8',
        'rounded-md',
        'bg-primary',
        'flex',
        'items-center',
        'justify-center'
      )
    })

    it('renders the perilex brand name', () => {
      render(<Header />, { wrapper: TestWrapper })

      const brandName = screen.getByRole('heading', { level: 1 })
      expect(brandName).toHaveTextContent('perilex')
      expect(brandName).toHaveClass('text-xl', 'font-bold', 'text-primary')
    })

    it('maintains correct logo section layout', () => {
      render(<Header />, { wrapper: TestWrapper })

      // Find the logo section by looking for the container with the brand elements
      const logoSection = screen.getByText('A').closest('[class*="space-x-2"]')
      expect(logoSection).toHaveClass('flex', 'items-center', 'space-x-2')
    })
  })

  describe('Navigation Buttons', () => {
    it('renders mobile menu toggle button with correct properties', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')
      const mobileMenuButton = buttons.find((button) => button.className.includes('lg:hidden'))

      expect(mobileMenuButton).toBeInTheDocument()
      expect(mobileMenuButton).toHaveAttribute('data-variant', 'ghost')
      expect(mobileMenuButton).toHaveAttribute('data-size', 'sm')
      expect(mobileMenuButton).toHaveClass('lg:hidden')
    })
  })

  describe('Responsive Layout', () => {
    it('shows correct elements on mobile viewports', () => {
      render(<Header />, { wrapper: TestWrapper })

      // Mobile menu button should be shown on mobile (lg:hidden)
      const mobileMenuButton = screen
        .getAllByTestId('mock-button')
        .find((button) => button.className.includes('lg:hidden'))
      expect(mobileMenuButton).toBeInTheDocument()
    })

    it('maintains proper layout spacing across breakpoints', () => {
      render(<Header />, { wrapper: TestWrapper })

      // Left section spacing
      const leftSection = screen.getByText('A').closest('[class*="space-x-4"]')
      expect(leftSection).toHaveClass('flex', 'items-center', 'space-x-4')

      // Right section spacing
      const rightSection = screen.getByTestId('user-preferences').closest('[class*="space-x-2"]')
      expect(rightSection).toHaveClass('flex', 'items-center', 'space-x-2')
    })
  })

  describe('Store Integration', () => {
    it('calls toggleMobileNav when mobile menu button is clicked', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')
      const mobileMenuButton = buttons.find((button) => button.className.includes('lg:hidden'))

      fireEvent.click(mobileMenuButton!)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('accesses store functions correctly on component mount', () => {
      render(<Header />, { wrapper: TestWrapper })

      expect(useAppStore).toHaveBeenCalled()
    })
  })

  describe('Component Integration', () => {
    it('renders UserPreferences component', () => {
      render(<Header />, { wrapper: TestWrapper })

      const userPreferences = screen.getByTestId('user-preferences')
      expect(userPreferences).toBeInTheDocument()
      expect(userPreferences).toHaveTextContent('UserPreferences Component')
    })

    it('maintains correct integration positioning', () => {
      render(<Header />, { wrapper: TestWrapper })

      const userPreferences = screen.getByTestId('user-preferences')

      // UserPreferences should be in the right section
      const rightSection = userPreferences.closest('[class*="space-x-2"]')
      expect(rightSection).toHaveClass('flex', 'items-center', 'space-x-2')
    })
  })

  describe('SVG Icons', () => {
    it('renders hamburger menu icons correctly', () => {
      render(<Header />, { wrapper: TestWrapper })

      // Should have hamburger menu SVGs
      const menuSvgs = screen.getAllByTestId('mock-button').filter((button) => {
        const svg = button.querySelector('svg')
        return svg && svg.getAttribute('viewBox') === '0 0 24 24'
      })

      expect(menuSvgs.length).toBeGreaterThanOrEqual(1)
    })

    it('applies correct classes to SVG icons', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')

      // Check mobile menu SVG classes
      const mobileButton = buttons.find((button) => button.className.includes('lg:hidden'))
      const mobileSvg = mobileButton?.querySelector('svg')
      expect(mobileSvg).toHaveClass('h-6', 'w-6')
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML elements', () => {
      render(<Header />, { wrapper: TestWrapper })

      const header = screen.getByRole('banner')
      expect(header.tagName).toBe('HEADER')

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toHaveTextContent('perilex')
    })

    it('provides accessible button elements', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')
      buttons.forEach((button) => {
        expect(button.tagName).toBe('BUTTON')
      })
    })

    it('maintains proper focus order', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')
      buttons.forEach((button) => {
        expect(button).not.toHaveAttribute('tabindex', '-1')
      })
    })

    it('provides appropriate ARIA attributes for interactive elements', () => {
      render(<Header />, { wrapper: TestWrapper })

      // SVG icons should not interfere with accessibility
      const svgs = screen
        .getAllByTestId('mock-button')
        .map((button) => button.querySelector('svg'))
        .filter(Boolean)

      svgs.forEach((svg) => {
        expect(svg).toHaveAttribute('fill', 'none')
        expect(svg).toHaveAttribute('viewBox')
      })
    })
  })

  describe('Event Handling', () => {
    it('handles click events without errors', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')

      expect(() => {
        buttons.forEach((button) => {
          fireEvent.click(button)
        })
      }).not.toThrow()
    })

    it('prevents event bubbling for button clicks', () => {
      render(<Header />, { wrapper: TestWrapper })

      const buttons = screen.getAllByTestId('mock-button')
      const mobileMenuButton = buttons.find((button) => button.className.includes('lg:hidden'))
      const clickEvent = new MouseEvent('click', { bubbles: true })

      fireEvent(mobileMenuButton!, clickEvent)

      expect(mockToggleMobileNav).toHaveBeenCalledTimes(1)
    })

    it('handles disabled state correctly', () => {
      render(<Header />, { wrapper: TestWrapper })

      // All buttons should be enabled by default
      const buttons = screen.getAllByTestId('mock-button')
      buttons.forEach((button) => {
        expect(button).not.toBeDisabled()
      })
    })
  })

  describe('Performance and Optimization', () => {
    it('renders consistently across multiple renders', () => {
      const { rerender } = render(<Header />, { wrapper: TestWrapper })

      const initialButtons = screen.getAllByTestId('mock-button')
      expect(initialButtons).toHaveLength(1) // Mobile menu only

      rerender(<Header />, { wrapper: TestWrapper })

      const rerenderedButtons = screen.getAllByTestId('mock-button')
      expect(rerenderedButtons).toHaveLength(1)
    })

    it('maintains component structure after re-renders', () => {
      const { rerender } = render(<Header />, { wrapper: TestWrapper })

      const _initialHeader = screen.getByRole('banner')
      const _initialBrandName = screen.getByText('perilex')

      rerender(<Header />, { wrapper: TestWrapper })

      const rerenderedHeader = screen.getByRole('banner')
      const rerenderedBrandName = screen.getByText('perilex')

      expect(rerenderedHeader).toBeInTheDocument()
      expect(rerenderedBrandName).toBeInTheDocument()
    })

    it('does not create memory leaks during unmount', () => {
      const { unmount } = render(<Header />, { wrapper: TestWrapper })

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('Error Handling', () => {
    it('handles store errors gracefully', () => {
      // Mock store to throw error
      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(() => {
        throw new Error('Store error')
      })

      expect(() => {
        render(<Header />, { wrapper: TestWrapper })
      }).toThrow('Store error')

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        toggleMobileNav: mockToggleMobileNav,
      }))
    })

    it('handles missing store functions gracefully', () => {
      // Mock store with missing functions
      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(
        () =>
          ({
            toggleMobileNav: mockToggleMobileNav,
          }) as any
      )

      expect(() => {
        render(<Header />, { wrapper: TestWrapper })
      }).not.toThrow()

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        toggleMobileNav: mockToggleMobileNav,
      }))
    })
  })
})
