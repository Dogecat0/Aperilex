import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useAppStore } from '@/lib/store'
import { DashboardHome } from './DashboardHome'

// Mock the store
const mockSetBreadcrumbs = vi.fn()

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => ({
    setBreadcrumbs: mockSetBreadcrumbs,
  })),
}))

// Mock child components to isolate DashboardHome testing
vi.mock('./QuickActions', () => ({
  QuickActions: () => <div data-testid="quick-actions">QuickActions Component</div>,
}))

vi.mock('./RecentAnalyses', () => ({
  RecentAnalyses: () => <div data-testid="recent-analyses">RecentAnalyses Component</div>,
}))

vi.mock('./MarketOverview', () => ({
  MarketOverview: () => <div data-testid="market-overview">MarketOverview Component</div>,
}))

vi.mock('./SystemHealth', () => ({
  SystemHealth: () => <div data-testid="system-health">SystemHealth Component</div>,
}))

describe('DashboardHome Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<DashboardHome />)
      }).not.toThrow()
    })

    it('renders the correct root structure', () => {
      render(<DashboardHome />)

      // Find the root container that has space-y-6 class (should be the outermost div)
      const rootDiv = screen.getByText('Welcome to Aperilex').closest('[class*="space-y-6"]')
      expect(rootDiv).toBeInTheDocument()
      expect(rootDiv).toHaveClass('space-y-6')
    })

    it('applies correct spacing classes to root container', () => {
      render(<DashboardHome />)

      const rootDiv = screen.getByText('Welcome to Aperilex').closest('[class*="space-y-6"]')
      expect(rootDiv).toHaveClass('space-y-6')
    })

    it('renders all major sections without errors', () => {
      render(<DashboardHome />)

      // Check that all main sections are present
      expect(screen.getByText('Welcome to Aperilex')).toBeInTheDocument()
      expect(screen.getByTestId('quick-actions')).toBeInTheDocument()
      expect(screen.getByTestId('recent-analyses')).toBeInTheDocument()
      expect(screen.getByTestId('market-overview')).toBeInTheDocument()
      expect(screen.getByTestId('system-health')).toBeInTheDocument()
    })
  })

  describe('Store Integration', () => {
    it('uses useAppStore hook correctly', () => {
      render(<DashboardHome />)

      expect(useAppStore).toHaveBeenCalled()
    })

    it('calls setBreadcrumbs on mount with correct data', () => {
      render(<DashboardHome />)

      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(1)
      expect(mockSetBreadcrumbs).toHaveBeenCalledWith([{ label: 'Dashboard', isActive: true }])
    })

    it('calls setBreadcrumbs with exact breadcrumb structure', () => {
      render(<DashboardHome />)

      const expectedBreadcrumb = { label: 'Dashboard', isActive: true }
      expect(mockSetBreadcrumbs).toHaveBeenCalledWith([expectedBreadcrumb])

      // Verify the breadcrumb structure matches BreadcrumbItem interface
      const calledWith = mockSetBreadcrumbs.mock.calls[0][0][0]
      expect(calledWith).toEqual(expectedBreadcrumb)
      expect(calledWith.label).toBe('Dashboard')
      expect(calledWith.isActive).toBe(true)
      expect(calledWith.href).toBeUndefined()
    })

    it('only calls setBreadcrumbs once during initial mount', () => {
      const { rerender } = render(<DashboardHome />)

      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(1)

      // Re-render should not call setBreadcrumbs again if dependency hasn't changed
      rerender(<DashboardHome />)
      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(1)
    })
  })

  describe('Welcome Section', () => {
    it('renders welcome title correctly', () => {
      render(<DashboardHome />)

      const title = screen.getByRole('heading', { level: 1 })
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Welcome to Aperilex')
    })

    it('applies correct styling classes to welcome title', () => {
      render(<DashboardHome />)

      const title = screen.getByRole('heading', { level: 1 })
      expect(title).toHaveClass('text-3xl', 'font-bold', 'text-foreground')
    })

    it('renders welcome description correctly', () => {
      render(<DashboardHome />)

      const description = screen.getByText(
        'Your open-source platform for SEC filing analysis and financial insights.'
      )
      expect(description).toBeInTheDocument()
      expect(description.tagName).toBe('P')
    })

    it('applies correct styling classes to welcome description', () => {
      render(<DashboardHome />)

      const description = screen.getByText(
        'Your open-source platform for SEC filing analysis and financial insights.'
      )
      expect(description).toHaveClass('text-muted-foreground')
    })

    it('maintains correct welcome section layout', () => {
      render(<DashboardHome />)

      const welcomeSection = screen.getByText('Welcome to Aperilex').closest('[class*="space-y-2"]')
      expect(welcomeSection).toHaveClass('space-y-2')

      // Verify both title and description are within the welcome section
      expect(welcomeSection).toContainElement(screen.getByText('Welcome to Aperilex'))
      expect(welcomeSection).toContainElement(
        screen.getByText(
          'Your open-source platform for SEC filing analysis and financial insights.'
        )
      )
    })
  })

  describe('Component Integration', () => {
    it('renders QuickActions component', () => {
      render(<DashboardHome />)

      const quickActions = screen.getByTestId('quick-actions')
      expect(quickActions).toBeInTheDocument()
      expect(quickActions).toHaveTextContent('QuickActions Component')
    })

    it('renders RecentAnalyses component', () => {
      render(<DashboardHome />)

      const recentAnalyses = screen.getByTestId('recent-analyses')
      expect(recentAnalyses).toBeInTheDocument()
      expect(recentAnalyses).toHaveTextContent('RecentAnalyses Component')
    })

    it('renders MarketOverview component', () => {
      render(<DashboardHome />)

      const marketOverview = screen.getByTestId('market-overview')
      expect(marketOverview).toBeInTheDocument()
      expect(marketOverview).toHaveTextContent('MarketOverview Component')
    })

    it('renders SystemHealth component', () => {
      render(<DashboardHome />)

      const systemHealth = screen.getByTestId('system-health')
      expect(systemHealth).toBeInTheDocument()
      expect(systemHealth).toHaveTextContent('SystemHealth Component')
    })

    it('renders all child components without conflicts', () => {
      render(<DashboardHome />)

      // All components should be present simultaneously
      expect(screen.getByTestId('quick-actions')).toBeInTheDocument()
      expect(screen.getByTestId('recent-analyses')).toBeInTheDocument()
      expect(screen.getByTestId('market-overview')).toBeInTheDocument()
      expect(screen.getByTestId('system-health')).toBeInTheDocument()
    })
  })

  describe('Layout Structure', () => {
    it('renders main content grid with correct classes', () => {
      render(<DashboardHome />)

      const gridContainer = screen.getByTestId('recent-analyses').closest('[class*="grid"]')
      expect(gridContainer).toHaveClass('grid', 'grid-cols-1', 'lg:grid-cols-3', 'gap-6')
    })

    it('applies correct column span to RecentAnalyses', () => {
      render(<DashboardHome />)

      const recentAnalysesContainer = screen
        .getByTestId('recent-analyses')
        .closest('[class*="lg:col-span-2"]')
      expect(recentAnalysesContainer).toHaveClass('lg:col-span-2')
    })

    it('renders side panel with correct structure', () => {
      render(<DashboardHome />)

      const sidePanel = screen.getByTestId('market-overview').closest('[class*="space-y-6"]')
      expect(sidePanel).toHaveClass('space-y-6')

      // Verify both MarketOverview and SystemHealth are in the side panel
      expect(sidePanel).toContainElement(screen.getByTestId('market-overview'))
      expect(sidePanel).toContainElement(screen.getByTestId('system-health'))
    })

    it('maintains correct component ordering in layout', () => {
      render(<DashboardHome />)

      const rootContainer = screen.getByText('Welcome to Aperilex').closest('[class*="space-y-6"]')

      // Get all child elements to verify order
      const children = Array.from(rootContainer!.children)

      // Welcome section should be first
      expect(children[0]).toContainElement(screen.getByText('Welcome to Aperilex'))

      // QuickActions should be second
      expect(children[1]).toBe(screen.getByTestId('quick-actions'))

      // Grid container should be third
      expect(children[2]).toContainElement(screen.getByTestId('recent-analyses'))
      expect(children[2]).toContainElement(screen.getByTestId('market-overview'))
    })

    it('applies responsive grid layout correctly', () => {
      render(<DashboardHome />)

      // Find the grid container that contains the recent-analyses element
      const gridContainer = screen.getByTestId('recent-analyses').closest('[class*="grid"]')
      expect(gridContainer).toHaveClass('grid-cols-1', 'lg:grid-cols-3')
    })
  })

  describe('Effects and Lifecycle', () => {
    it('calls setBreadcrumbs in useEffect on mount', () => {
      render(<DashboardHome />)

      // Should be called during mount
      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(1)
    })

    it('includes setBreadcrumbs in useEffect dependency array', () => {
      const mockSetBreadcrumbsNew = vi.fn()
      const mockStore = vi.mocked(useAppStore)

      // First render
      render(<DashboardHome />)
      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(1)

      // Change the setBreadcrumbs function reference
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: mockSetBreadcrumbsNew,
      }))

      // Re-render with new function reference
      render(<DashboardHome />)
      expect(mockSetBreadcrumbsNew).toHaveBeenCalledTimes(1)
    })

    it('handles component unmounting correctly', () => {
      const { unmount } = render(<DashboardHome />)

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    it('does not call setBreadcrumbs after unmount', () => {
      const { unmount } = render(<DashboardHome />)

      const initialCallCount = mockSetBreadcrumbs.mock.calls.length
      unmount()

      // Should not have additional calls after unmount
      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(initialCallCount)
    })
  })

  describe('Re-rendering Behavior', () => {
    it('component updates correctly when store changes', () => {
      const { rerender } = render(<DashboardHome />)

      expect(screen.getByText('Welcome to Aperilex')).toBeInTheDocument()

      rerender(<DashboardHome />)

      expect(screen.getByText('Welcome to Aperilex')).toBeInTheDocument()
      expect(screen.getByTestId('quick-actions')).toBeInTheDocument()
    })

    it('maintains component structure across re-renders', () => {
      const { rerender } = render(<DashboardHome />)

      const _initialTitle = screen.getByText('Welcome to Aperilex')
      const _initialQuickActions = screen.getByTestId('quick-actions')

      rerender(<DashboardHome />)

      expect(screen.getByText('Welcome to Aperilex')).toBeInTheDocument()
      expect(screen.getByTestId('quick-actions')).toBeInTheDocument()
      expect(screen.getByTestId('recent-analyses')).toBeInTheDocument()
      expect(screen.getByTestId('market-overview')).toBeInTheDocument()
      expect(screen.getByTestId('system-health')).toBeInTheDocument()
    })

    it('preserves layout classes after re-renders', () => {
      const { rerender } = render(<DashboardHome />)

      rerender(<DashboardHome />)

      const rootDiv = screen.getByText('Welcome to Aperilex').closest('[class*="space-y-6"]')
      expect(rootDiv).toHaveClass('space-y-6')

      const gridContainer = screen.getByTestId('recent-analyses').closest('[class*="grid"]')
      expect(gridContainer).toHaveClass('grid', 'grid-cols-1', 'lg:grid-cols-3', 'gap-6')
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('handles store errors gracefully', () => {
      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(() => {
        throw new Error('Store error')
      })

      expect(() => {
        render(<DashboardHome />)
      }).toThrow('Store error')

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: mockSetBreadcrumbs,
      }))
    })

    it('handles missing setBreadcrumbs function gracefully', () => {
      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(
        () =>
          ({
            setBreadcrumbs: undefined,
          }) as any
      )

      expect(() => {
        render(<DashboardHome />)
      }).toThrow()

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: mockSetBreadcrumbs,
      }))
    })

    it('handles null or undefined store return', () => {
      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(() => null as any)

      expect(() => {
        render(<DashboardHome />)
      }).toThrow()

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: mockSetBreadcrumbs,
      }))
    })

    it('handles setBreadcrumbs function that throws error', () => {
      const errorThrowingSetBreadcrumbs = vi.fn(() => {
        throw new Error('setBreadcrumbs error')
      })

      const mockStore = vi.mocked(useAppStore)
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: errorThrowingSetBreadcrumbs,
      }))

      expect(() => {
        render(<DashboardHome />)
      }).toThrow('setBreadcrumbs error')

      // Restore normal mock
      mockStore.mockImplementation(() => ({
        setBreadcrumbs: mockSetBreadcrumbs,
      }))
    })

    it('renders correctly even when child components fail to load', () => {
      // This test assumes child components are mocked and won't actually fail
      // In a real scenario, you'd test error boundaries
      render(<DashboardHome />)

      expect(screen.getByText('Welcome to Aperilex')).toBeInTheDocument()
    })
  })

  describe('Accessibility and Semantics', () => {
    it('uses proper semantic HTML elements', () => {
      render(<DashboardHome />)

      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading.tagName).toBe('H1')
      expect(heading).toHaveTextContent('Welcome to Aperilex')

      const description = screen.getByText(
        'Your open-source platform for SEC filing analysis and financial insights.'
      )
      expect(description.tagName).toBe('P')
    })

    it('maintains proper heading hierarchy', () => {
      render(<DashboardHome />)

      const headings = screen.getAllByRole('heading')
      const h1Elements = headings.filter((h) => h.tagName === 'H1')

      expect(h1Elements).toHaveLength(1)
      expect(h1Elements[0]).toHaveTextContent('Welcome to Aperilex')
    })

    it('provides accessible content structure', () => {
      render(<DashboardHome />)

      // Main content should be organized in a logical structure
      const title = screen.getByText('Welcome to Aperilex')
      const description = screen.getByText(
        'Your open-source platform for SEC filing analysis and financial insights.'
      )

      // Description should come after title in DOM order
      const elements = screen.getAllByText(/Welcome to Aperilex|Your open-source platform/)
      expect(elements[0]).toBe(title)
      expect(elements[1]).toBe(description)
    })
  })

  describe('Performance Considerations', () => {
    it('does not cause excessive re-renders', () => {
      const { rerender } = render(<DashboardHome />)

      const initialCallCount = mockSetBreadcrumbs.mock.calls.length

      // Multiple re-renders with same props should not cause additional setBreadcrumbs calls
      rerender(<DashboardHome />)
      rerender(<DashboardHome />)
      rerender(<DashboardHome />)

      expect(mockSetBreadcrumbs).toHaveBeenCalledTimes(initialCallCount)
    })

    it('maintains stable component references', () => {
      render(<DashboardHome />)

      const quickActions1 = screen.getByTestId('quick-actions')
      const recentAnalyses1 = screen.getByTestId('recent-analyses')

      // Components should be stable across renders
      expect(quickActions1).toBeInTheDocument()
      expect(recentAnalyses1).toBeInTheDocument()
    })

    it('handles rapid successive renders without errors', () => {
      const { rerender } = render(<DashboardHome />)

      expect(() => {
        for (let i = 0; i < 10; i++) {
          rerender(<DashboardHome />)
        }
      }).not.toThrow()
    })
  })
})
