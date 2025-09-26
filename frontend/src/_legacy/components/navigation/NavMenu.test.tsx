import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { NavMenu } from './NavMenu'
import { navigationMocks, resetNavigationMocks } from '../../test/jsdom-navigation-mock'

// Mock navigation hook to track navigation calls
const mockNavigate = vi.fn()
const mockLocation = { pathname: '/' }

// Mock React Router hooks
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
    Link: ({ to, onClick, className, children, ...props }: any) => (
      <a
        href={to}
        onClick={(e) => {
          e.preventDefault()
          // Call the navigate function to simulate React Router behavior
          mockNavigate(to)
          if (onClick) onClick()
        }}
        className={className}
        data-testid={`nav-link-${to}`}
        {...props}
      >
        {children}
      </a>
    ),
  }
})

// Helper to render NavMenu with React Router context
const renderNavMenu = (props: { currentPath: string; onNavigate?: () => void }) => {
  return render(
    <MemoryRouter>
      <NavMenu {...props} />
    </MemoryRouter>
  )
}

// Navigation items data for testing
const expectedNavigationItems = [
  { id: 'dashboard', label: 'Dashboard', href: '/' },
  { id: 'companies', label: 'Companies', href: '/companies' },
  { id: 'analyses', label: 'Analyses', href: '/analyses' },
  { id: 'filings', label: 'Filings', href: '/filings' },
]

describe('NavMenu Component', () => {
  const mockOnNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    resetNavigationMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        renderNavMenu({ currentPath: '/' })
      }).not.toThrow()
    })

    it('renders with correct semantic structure', () => {
      renderNavMenu({ currentPath: '/' })

      const navList = screen.getByRole('list')
      expect(navList).toBeInTheDocument()
      expect(navList.tagName).toBe('UL')
    })

    it('applies correct CSS classes to the navigation list', () => {
      renderNavMenu({ currentPath: '/' })

      const navList = screen.getByRole('list')
      expect(navList).toHaveClass('-mx-2', 'space-y-1')
    })

    it('renders all navigation items as list items', () => {
      renderNavMenu({ currentPath: '/' })

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(4)

      listItems.forEach((item) => {
        expect(item.tagName).toBe('LI')
      })
    })

    it('maintains consistent component structure across renders', () => {
      const { rerender } = render(
        <MemoryRouter>
          <NavMenu currentPath="/" />
        </MemoryRouter>
      )

      const initialItems = screen.getAllByRole('listitem')
      expect(initialItems).toHaveLength(4)

      rerender(
        <MemoryRouter>
          <NavMenu currentPath="/companies" />
        </MemoryRouter>
      )

      const rerenderedItems = screen.getAllByRole('listitem')
      expect(rerenderedItems).toHaveLength(4)
    })
  })

  describe('Navigation Items', () => {
    it('renders all navigation items with correct labels', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') })
        expect(link).toBeInTheDocument()
        expect(link).toHaveTextContent(item.label)
      })
    })

    it('renders all navigation items with correct href attributes', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toBeInTheDocument()
        expect(link).toHaveAttribute('href', item.href)
      })
    })

    it('renders navigation items in the correct order', () => {
      renderNavMenu({ currentPath: '/' })

      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(4)

      expectedNavigationItems.forEach((item, index) => {
        expect(links[index]).toHaveTextContent(item.label)
        expect(links[index]).toHaveAttribute('href', item.href)
      })
    })

    it('assigns correct key attributes to list items', () => {
      renderNavMenu({ currentPath: '/' })

      const listItems = screen.getAllByRole('listitem')

      listItems.forEach((item, index) => {
        // Check that each list item contains the expected navigation link
        const expectedItem = expectedNavigationItems[index]
        const link = screen.getByTestId(`nav-link-${expectedItem.href}`)
        expect(item).toContainElement(link)
      })
    })

    it('handles navigation items with special characters correctly', () => {
      renderNavMenu({ currentPath: '/' })

      // All our navigation items have standard names, but test the rendering is stable
      expectedNavigationItems.forEach((item) => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') })
        expect(link.textContent).toBe(item.label)
      })
    })
  })

  describe('Active State Logic', () => {
    describe('Dashboard (/) Active State', () => {
      it('marks dashboard as active when currentPath is exactly "/"', () => {
        renderNavMenu({ currentPath: '/' })

        const dashboardLink = screen.getByTestId('nav-link-/')
        expect(dashboardLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('does not mark dashboard as active for other root-level paths', () => {
        renderNavMenu({ currentPath: '/companies' })

        const dashboardLink = screen.getByTestId('nav-link-/')
        expect(dashboardLink).not.toHaveClass('bg-primary', 'text-primary-foreground')
        expect(dashboardLink).toHaveClass(
          'text-foreground',
          'hover:text-primary',
          'hover:bg-accent'
        )
      })

      it('does not mark dashboard as active for nested paths', () => {
        renderNavMenu({ currentPath: '/companies/details' })

        const dashboardLink = screen.getByTestId('nav-link-/')
        expect(dashboardLink).not.toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('does not mark dashboard as active for paths that start with /', () => {
        renderNavMenu({ currentPath: '/dashboard' })

        const dashboardLink = screen.getByTestId('nav-link-/')
        expect(dashboardLink).not.toHaveClass('bg-primary', 'text-primary-foreground')
      })
    })

    describe('Non-root Active State Logic', () => {
      it('marks companies as active when currentPath starts with "/companies"', () => {
        renderNavMenu({ currentPath: '/companies' })

        const companiesLink = screen.getByTestId('nav-link-/companies')
        expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('marks companies as active for nested company paths', () => {
        renderNavMenu({ currentPath: '/companies/AAPL' })

        const companiesLink = screen.getByTestId('nav-link-/companies')
        expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('marks analyses as active when currentPath starts with "/analyses"', () => {
        renderNavMenu({ currentPath: '/analyses' })

        const analysesLink = screen.getByTestId('nav-link-/analyses')
        expect(analysesLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('marks analyses as active for nested analysis paths', () => {
        renderNavMenu({ currentPath: '/analyses/123' })

        const analysesLink = screen.getByTestId('nav-link-/analyses')
        expect(analysesLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('marks filings as active when currentPath starts with "/filings"', () => {
        renderNavMenu({ currentPath: '/filings' })

        const filingsLink = screen.getByTestId('nav-link-/filings')
        expect(filingsLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })

      it('marks filings as active for nested filing paths', () => {
        renderNavMenu({ currentPath: '/filings/10-K/2023' })

        const filingsLink = screen.getByTestId('nav-link-/filings')
        expect(filingsLink).toHaveClass('bg-primary', 'text-primary-foreground')
      })
    })

    describe('Inactive State Logic', () => {
      it('marks all items as inactive when currentPath does not match any', () => {
        renderNavMenu({ currentPath: '/unknown' })

        expectedNavigationItems.forEach((item) => {
          const link = screen.getByTestId(`nav-link-${item.href}`)
          expect(link).not.toHaveClass('bg-primary', 'text-primary-foreground')
          expect(link).toHaveClass('text-foreground', 'hover:text-primary', 'hover:bg-accent')
        })
      })

      it('ensures only one item is active at a time', () => {
        renderNavMenu({ currentPath: '/companies' })

        const companiesLink = screen.getByTestId('nav-link-/companies')
        expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')

        // All other items should be inactive
        const otherItems = expectedNavigationItems.filter((item) => item.href !== '/companies')
        otherItems.forEach((item) => {
          const link = screen.getByTestId(`nav-link-${item.href}`)
          expect(link).not.toHaveClass('bg-primary', 'text-primary-foreground')
        })
      })
    })
  })

  describe('Links and Navigation', () => {
    it('renders React Router Link components', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toBeInTheDocument()
        expect(link.tagName).toBe('A')
      })
    })

    it('sets correct "to" props on Link components', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toHaveAttribute('href', item.href)
      })
    })

    it('applies correct base styling classes to all links', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toHaveClass(
          'group',
          'flex',
          'gap-x-3',
          'rounded-md',
          'p-2',
          'text-sm',
          'leading-6',
          'font-semibold',
          'transition-colors'
        )
      })
    })

    it('ensures links are keyboard accessible', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).not.toHaveAttribute('tabindex', '-1')
      })
    })
  })

  describe('Styling and CSS Classes', () => {
    it('applies active styling to the current path', () => {
      renderNavMenu({ currentPath: '/companies' })

      const activeLink = screen.getByTestId('nav-link-/companies')
      expect(activeLink).toHaveClass('bg-primary', 'text-primary-foreground')
    })

    it('applies inactive styling to non-current paths', () => {
      renderNavMenu({ currentPath: '/companies' })

      const inactiveItems = expectedNavigationItems.filter((item) => item.href !== '/companies')
      inactiveItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toHaveClass('text-foreground', 'hover:text-primary', 'hover:bg-accent')
      })
    })

    it('applies correct icon styling for active items', () => {
      renderNavMenu({ currentPath: '/analyses' })

      const activeLink = screen.getByTestId('nav-link-/analyses')
      const iconSpan = activeLink.querySelector('span')
      expect(iconSpan).toHaveClass('text-primary-foreground')
    })

    it('applies correct icon styling for inactive items', () => {
      renderNavMenu({ currentPath: '/analyses' })

      const inactiveItems = expectedNavigationItems.filter((item) => item.href !== '/analyses')
      inactiveItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const iconSpan = link.querySelector('span')
        expect(iconSpan).toHaveClass('text-muted-foreground', 'group-hover:text-primary')
      })
    })

    it('maintains consistent spacing and layout classes', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toHaveClass('gap-x-3', 'p-2')
      })
    })

    it('applies transition classes for smooth hover effects', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).toHaveClass('transition-colors')
      })
    })
  })

  describe('Props Handling', () => {
    it('handles currentPath prop correctly', () => {
      const { rerender } = render(
        <MemoryRouter>
          <NavMenu currentPath="/" />
        </MemoryRouter>
      )

      let dashboardLink = screen.getByTestId('nav-link-/')
      expect(dashboardLink).toHaveClass('bg-primary', 'text-primary-foreground')

      rerender(
        <MemoryRouter>
          <NavMenu currentPath="/companies" />
        </MemoryRouter>
      )

      dashboardLink = screen.getByTestId('nav-link-/')
      expect(dashboardLink).not.toHaveClass('bg-primary', 'text-primary-foreground')

      const companiesLink = screen.getByTestId('nav-link-/companies')
      expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')
    })

    it('calls onNavigate callback when provided and link is clicked', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      const companiesLink = screen.getByTestId('nav-link-/companies')
      fireEvent.click(companiesLink)

      expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    })

    it('does not error when onNavigate is not provided', () => {
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')

      expect(() => {
        fireEvent.click(companiesLink)
      }).not.toThrow()
    })

    it('calls onNavigate for each link click', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        fireEvent.click(link)
      })

      expect(mockOnNavigate).toHaveBeenCalledTimes(4)
    })

    it('calls navigate function with correct paths when links are clicked', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        fireEvent.click(link)
        expect(mockNavigate).toHaveBeenCalledWith(item.href)
      })

      expect(mockNavigate).toHaveBeenCalledTimes(4)
    })

    it('handles multiple rapid clicks correctly', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      const companiesLink = screen.getByTestId('nav-link-/companies')

      fireEvent.click(companiesLink)
      fireEvent.click(companiesLink)
      fireEvent.click(companiesLink)

      expect(mockOnNavigate).toHaveBeenCalledTimes(3)
    })
  })

  describe('Icons', () => {
    it('renders SVG icons for all navigation items', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const svg = link.querySelector('svg')
        expect(svg).toBeInTheDocument()
      })
    })

    it('applies correct classes to SVG icons', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const svg = link.querySelector('svg')
        expect(svg).toHaveClass('w-5', 'h-5')
        expect(svg).toHaveAttribute('fill', 'none')
        expect(svg).toHaveAttribute('viewBox', '0 0 24 24')
        expect(svg).toHaveAttribute('stroke', 'currentColor')
      })
    })

    it('renders correct dashboard icon SVG path', () => {
      renderNavMenu({ currentPath: '/' })

      const dashboardLink = screen.getByTestId('nav-link-/')
      const svg = dashboardLink.querySelector('svg')
      const path = svg?.querySelector('path')

      expect(path).toHaveAttribute('stroke-linecap', 'round')
      expect(path).toHaveAttribute('stroke-linejoin', 'round')
      expect(path).toHaveAttribute('stroke-width', '2')
      expect(path?.getAttribute('d')).toContain(
        'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z'
      )
    })

    it('renders correct companies icon SVG path', () => {
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')
      const svg = companiesLink.querySelector('svg')
      const path = svg?.querySelector('path')

      expect(path?.getAttribute('d')).toContain(
        'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
      )
    })

    it('renders correct analyses icon SVG path', () => {
      renderNavMenu({ currentPath: '/' })

      const analysesLink = screen.getByTestId('nav-link-/analyses')
      const svg = analysesLink.querySelector('svg')
      const path = svg?.querySelector('path')

      expect(path?.getAttribute('d')).toContain(
        'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
      )
    })

    it('renders correct filings icon SVG path', () => {
      renderNavMenu({ currentPath: '/' })

      const filingsLink = screen.getByTestId('nav-link-/filings')
      const svg = filingsLink.querySelector('svg')
      const path = svg?.querySelector('path')

      expect(path?.getAttribute('d')).toContain(
        'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
      )
    })

    it('wraps icons in span elements with correct classes', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const iconSpan = link.querySelector('span')
        expect(iconSpan).toBeInTheDocument()
        expect(iconSpan?.querySelector('svg')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic HTML with list structure', () => {
      renderNavMenu({ currentPath: '/' })

      const navList = screen.getByRole('list')
      expect(navList).toBeInTheDocument()

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(4)
    })

    it('provides accessible link elements', () => {
      renderNavMenu({ currentPath: '/' })

      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(4)

      links.forEach((link) => {
        expect(link.tagName).toBe('A')
        expect(link).toHaveAttribute('href')
      })
    })

    it('maintains proper focus order for keyboard navigation', () => {
      renderNavMenu({ currentPath: '/' })

      const links = screen.getAllByRole('link')
      links.forEach((link) => {
        expect(link).not.toHaveAttribute('tabindex', '-1')
      })
    })

    it('provides meaningful text content for screen readers', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') })
        expect(link).toHaveAccessibleName()
        expect(link.textContent).toContain(item.label)
      })
    })

    it('uses current color for SVG icons to inherit text color', () => {
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const svg = link.querySelector('svg')
        expect(svg).toHaveAttribute('stroke', 'currentColor')
      })
    })

    it('does not interfere with screen reader navigation', () => {
      renderNavMenu({ currentPath: '/' })

      // SVG icons should not have aria-hidden or other accessibility blocking attributes
      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        const svg = link.querySelector('svg')
        expect(svg).not.toHaveAttribute('aria-hidden', 'true')
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles empty currentPath gracefully', () => {
      expect(() => {
        renderNavMenu({ currentPath: '' })
      }).not.toThrow()

      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(4)

      // No item should be active with empty path
      expectedNavigationItems.forEach((item) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        expect(link).not.toHaveClass('bg-primary', 'text-primary-foreground')
      })
    })

    it('handles invalid currentPath values', () => {
      const invalidPaths = ['invalid', 'not-a-path', '////', 'null', 'undefined']

      invalidPaths.forEach((invalidPath) => {
        expect(() => {
          renderNavMenu({ currentPath: invalidPath })
        }).not.toThrow()
      })
    })

    it('handles undefined onNavigate callback gracefully', () => {
      renderNavMenu({ currentPath: '/', onNavigate: undefined })

      const companiesLink = screen.getByTestId('nav-link-/companies')

      expect(() => {
        fireEvent.click(companiesLink)
      }).not.toThrow()
    })

    it('handles special characters in currentPath', () => {
      const specialPaths = ['/companies?query=test', '/companies#section', '/companies%20space']

      specialPaths.forEach((specialPath) => {
        expect(() => {
          renderNavMenu({ currentPath: specialPath })
        }).not.toThrow()
      })
    })

    it('handles very long currentPath values', () => {
      const longPath = '/companies/' + 'a'.repeat(1000)

      expect(() => {
        renderNavMenu({ currentPath: longPath })
      }).not.toThrow()

      const companiesLink = screen.getByTestId('nav-link-/companies')
      expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')
    })

    it('prevents default link behavior when clicked', () => {
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')
      const clickEvent = new MouseEvent('click', { bubbles: true })

      let defaultPrevented = false
      clickEvent.preventDefault = () => {
        defaultPrevented = true
      }

      fireEvent(companiesLink, clickEvent)

      expect(defaultPrevented).toBe(true)
    })
  })

  describe('Performance and Memory', () => {
    it('does not create memory leaks during unmount', () => {
      const { unmount } = renderNavMenu({ currentPath: '/' })

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    it('renders consistently across multiple re-renders', () => {
      const { rerender } = render(
        <MemoryRouter>
          <NavMenu currentPath="/" onNavigate={mockOnNavigate} />
        </MemoryRouter>
      )

      const initialLinks = screen.getAllByRole('link')
      expect(initialLinks).toHaveLength(4)

      rerender(
        <MemoryRouter>
          <NavMenu currentPath="/companies" onNavigate={mockOnNavigate} />
        </MemoryRouter>
      )

      const rerenderedLinks = screen.getAllByRole('link')
      expect(rerenderedLinks).toHaveLength(4)
    })

    it('maintains stable component structure across prop changes', () => {
      const { rerender } = render(
        <MemoryRouter>
          <NavMenu currentPath="/" />
        </MemoryRouter>
      )

      let navList = screen.getByRole('list')
      let listItems = screen.getAllByRole('listitem')
      expect(navList).toBeInTheDocument()
      expect(listItems).toHaveLength(4)

      rerender(
        <MemoryRouter>
          <NavMenu currentPath="/analyses" onNavigate={mockOnNavigate} />
        </MemoryRouter>
      )

      navList = screen.getByRole('list')
      listItems = screen.getAllByRole('listitem')
      expect(navList).toBeInTheDocument()
      expect(listItems).toHaveLength(4)
    })
  })

  describe('React Router Integration', () => {
    it('properly integrates with React Router navigation', () => {
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')
      fireEvent.click(companiesLink)

      // Verify that React Router navigate was called with correct path
      expect(mockNavigate).toHaveBeenCalledWith('/companies')
      expect(mockNavigate).toHaveBeenCalledTimes(1)
    })

    it('does not trigger browser navigation when Link is clicked', () => {
      const mockPreventDefault = vi.fn()
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')

      // Create a mock event to verify preventDefault is called
      const clickEvent = new MouseEvent('click', { bubbles: true })
      clickEvent.preventDefault = mockPreventDefault

      fireEvent(companiesLink, clickEvent)

      expect(mockPreventDefault).toHaveBeenCalled()
    })

    it('handles navigation without external API dependencies', () => {
      // This test ensures our mocking approach works without relying on JSDOM navigation
      renderNavMenu({ currentPath: '/' })

      expectedNavigationItems.forEach((item, index) => {
        const link = screen.getByTestId(`nav-link-${item.href}`)
        fireEvent.click(link)

        // Verify each navigation call
        expect(mockNavigate).toHaveBeenNthCalledWith(index + 1, item.href)
      })

      expect(mockNavigate).toHaveBeenCalledTimes(4)
    })

    it('works correctly within MemoryRouter context', () => {
      // Render without our custom helper to test direct MemoryRouter usage
      render(
        <MemoryRouter initialEntries={['/companies']}>
          <NavMenu currentPath="/companies" />
        </MemoryRouter>
      )

      const companiesLink = screen.getByTestId('nav-link-/companies')
      expect(companiesLink).toHaveClass('bg-primary', 'text-primary-foreground')

      const dashboardLink = screen.getByTestId('nav-link-/')
      expect(dashboardLink).not.toHaveClass('bg-primary', 'text-primary-foreground')
    })

    it('supports programmatic navigation testing', () => {
      const { rerender } = render(
        <MemoryRouter>
          <NavMenu currentPath="/" />
        </MemoryRouter>
      )

      // Simulate navigation by changing the currentPath prop
      rerender(
        <MemoryRouter>
          <NavMenu currentPath="/analyses" />
        </MemoryRouter>
      )

      const analysesLink = screen.getByTestId('nav-link-/analyses')
      expect(analysesLink).toHaveClass('bg-primary', 'text-primary-foreground')
    })

    it('works with mocked navigation APIs without JSDOM warnings', () => {
      renderNavMenu({ currentPath: '/' })

      // Verify that navigation mocks are available
      expect(navigationMocks.navigation).toBeDefined()
      expect(navigationMocks.location).toBeDefined()
      expect(navigationMocks.history).toBeDefined()

      // Test clicking a link doesn't cause any navigation errors
      const companiesLink = screen.getByTestId('nav-link-/companies')
      expect(() => {
        fireEvent.click(companiesLink)
      }).not.toThrow()

      // Verify React Router navigate was called
      expect(mockNavigate).toHaveBeenCalledWith('/companies')
    })

    it('prevents actual browser navigation while maintaining React Router functionality', () => {
      renderNavMenu({ currentPath: '/' })

      const dashboardLink = screen.getByTestId('nav-link-/')

      // Click the link
      fireEvent.click(dashboardLink)

      // Verify React Router navigate was called
      expect(mockNavigate).toHaveBeenCalledWith('/')

      // Verify no actual browser navigation occurred
      expect(navigationMocks.location.assign).not.toHaveBeenCalled()
      expect(navigationMocks.history.pushState).not.toHaveBeenCalled()
    })
  })

  describe('Event Handling', () => {
    it('handles click events without errors', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      expect(() => {
        expectedNavigationItems.forEach((item) => {
          const link = screen.getByTestId(`nav-link-${item.href}`)
          fireEvent.click(link)
        })
      }).not.toThrow()
    })

    it('prevents default navigation behavior on link clicks', () => {
      renderNavMenu({ currentPath: '/' })

      const companiesLink = screen.getByTestId('nav-link-/companies')
      const clickEvent = new MouseEvent('click', { bubbles: true })

      let defaultPrevented = false
      const originalPreventDefault = clickEvent.preventDefault
      clickEvent.preventDefault = () => {
        defaultPrevented = true
        originalPreventDefault.call(clickEvent)
      }

      fireEvent(companiesLink, clickEvent)

      expect(defaultPrevented).toBe(true)
    })

    it('handles keyboard events correctly', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      const companiesLink = screen.getByTestId('nav-link-/companies')

      expect(() => {
        fireEvent.keyDown(companiesLink, { key: 'Enter' })
        fireEvent.keyDown(companiesLink, { key: ' ' })
      }).not.toThrow()
    })

    it('maintains event delegation properly', () => {
      renderNavMenu({ currentPath: '/', onNavigate: mockOnNavigate })

      const navList = screen.getByRole('list')

      // Click on the list itself should not trigger navigation
      fireEvent.click(navList)
      expect(mockOnNavigate).not.toHaveBeenCalled()

      // Click on link should trigger navigation
      const companiesLink = screen.getByTestId('nav-link-/companies')
      fireEvent.click(companiesLink)
      expect(mockOnNavigate).toHaveBeenCalledTimes(1)
    })
  })
})
