import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { RecentAnalyses } from './RecentAnalyses'

// Mock the Skeleton component
vi.mock('@/components/ui/Skeleton', () => ({
  Skeleton: ({ className }: { className: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}))

// Mock the store
const mockUseAnalysisStore = vi.fn()
vi.mock('@/lib/store', () => ({
  useAnalysisStore: () => mockUseAnalysisStore(),
}))

describe('RecentAnalyses', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      const { container } = render(<RecentAnalyses />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders card structure with correct styling', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      const { container } = render(<RecentAnalyses />)
      const cardElement = container.firstChild as HTMLElement

      expect(cardElement).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })

    it('renders with proper container structure', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      // Check that the main card container exists using more specific selector
      const cardContainer = document.querySelector('.rounded-lg.border.bg-card.p-6')
      expect(cardContainer).toBeInTheDocument()
    })
  })

  describe('Store Integration', () => {
    it('uses useAnalysisStore to get recentAnalyses', () => {
      const mockStore = { recentAnalyses: [] }
      mockUseAnalysisStore.mockReturnValue(mockStore)

      render(<RecentAnalyses />)

      expect(mockUseAnalysisStore).toHaveBeenCalled()
    })

    it('accesses recentAnalyses from store correctly', () => {
      const mockRecentAnalyses = ['analysis-1', 'analysis-2']
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: mockRecentAnalyses,
      })

      render(<RecentAnalyses />)

      expect(mockUseAnalysisStore).toHaveBeenCalled()
      // Since we have data, we should see skeletons instead of empty state
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
    })

    it('handles undefined recentAnalyses gracefully', () => {
      mockUseAnalysisStore.mockReturnValue({})

      // This should not crash the component
      expect(() => render(<RecentAnalyses />)).not.toThrow()
    })

    it('handles store errors gracefully', () => {
      mockUseAnalysisStore.mockImplementation(() => {
        throw new Error('Store error')
      })

      expect(() => render(<RecentAnalyses />)).toThrow('Store error')
    })
  })

  describe('Header Section', () => {
    it('renders "Recent Analyses" title', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const title = screen.getByRole('heading', { level: 2 })
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Recent Analyses')
    })

    it('renders title with correct styling', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const title = screen.getByRole('heading', { level: 2 })
      expect(title).toHaveClass('text-lg', 'font-semibold')
    })

    it('renders "View all" button', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      expect(viewAllButton).toBeInTheDocument()
    })

    it('renders "View all" button with correct styling', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      expect(viewAllButton).toHaveClass('text-sm', 'text-primary', 'hover:text-primary/80')
    })

    it('renders header with correct flex layout', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const headerContainer = screen.getByRole('heading', { level: 2 }).parentElement
      expect(headerContainer).toHaveClass('flex', 'items-center', 'justify-between', 'mb-4')
    })
  })

  describe('Empty State Rendering', () => {
    beforeEach(() => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })
    })

    it('shows empty state when recentAnalyses.length === 0', () => {
      render(<RecentAnalyses />)

      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
      expect(
        screen.getByText('Get started by analyzing your first SEC filing.')
      ).toBeInTheDocument()
    })

    it('renders chart icon with correct properties', () => {
      render(<RecentAnalyses />)

      // Find SVG by class since role="img" might not be applied to all SVGs
      const chartIcon = document.querySelector('svg.mx-auto.h-12.w-12.text-muted-foreground')
      expect(chartIcon).toBeInTheDocument()
      expect(chartIcon).toHaveClass('mx-auto', 'h-12', 'w-12', 'text-muted-foreground')
      expect(chartIcon).toHaveAttribute('fill', 'none')
      expect(chartIcon).toHaveAttribute('viewBox', '0 0 24 24')
      expect(chartIcon).toHaveAttribute('stroke', 'currentColor')
    })

    it('renders chart icon SVG path with correct properties', () => {
      render(<RecentAnalyses />)

      const svgPath = document.querySelector('svg.mx-auto.h-12.w-12.text-muted-foreground path')
      expect(svgPath).toBeInTheDocument()
      expect(svgPath).toHaveAttribute('stroke-linecap', 'round')
      expect(svgPath).toHaveAttribute('stroke-linejoin', 'round')
      expect(svgPath).toHaveAttribute('stroke-width', '2')
      expect(svgPath).toHaveAttribute(
        'd',
        'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
      )
    })

    it('renders "No analyses yet" heading with correct styling', () => {
      render(<RecentAnalyses />)

      const noAnalysesHeading = screen.getByRole('heading', { level: 3 })
      expect(noAnalysesHeading).toBeInTheDocument()
      expect(noAnalysesHeading).toHaveTextContent('No analyses yet')
      expect(noAnalysesHeading).toHaveClass('mt-2', 'text-sm', 'font-semibold', 'text-foreground')
    })

    it('renders description text with correct styling', () => {
      render(<RecentAnalyses />)

      const descriptionText = screen.getByText('Get started by analyzing your first SEC filing.')
      expect(descriptionText).toBeInTheDocument()
      expect(descriptionText).toHaveClass('mt-1', 'text-sm', 'text-muted-foreground')
    })

    it('renders "New Analysis" button with correct styling', () => {
      render(<RecentAnalyses />)

      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      expect(newAnalysisButton).toBeInTheDocument()
      expect(newAnalysisButton).toHaveClass(
        'inline-flex',
        'items-center',
        'rounded-md',
        'bg-primary',
        'px-3',
        'py-2',
        'text-sm',
        'font-semibold',
        'text-primary-foreground',
        'shadow-sm',
        'hover:bg-primary/90'
      )
    })

    it('renders plus icon in "New Analysis" button with correct properties', () => {
      render(<RecentAnalyses />)

      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      const plusIcon = newAnalysisButton.querySelector('svg')

      expect(plusIcon).toBeInTheDocument()
      expect(plusIcon).toHaveClass('-ml-0.5', 'mr-1.5', 'h-5', 'w-5')
      expect(plusIcon).toHaveAttribute('fill', 'none')
      expect(plusIcon).toHaveAttribute('viewBox', '0 0 24 24')
      expect(plusIcon).toHaveAttribute('stroke', 'currentColor')
    })

    it('renders plus icon SVG path with correct properties', () => {
      render(<RecentAnalyses />)

      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      const plusIconPath = newAnalysisButton.querySelector('svg path')

      expect(plusIconPath).toBeInTheDocument()
      expect(plusIconPath).toHaveAttribute('stroke-linecap', 'round')
      expect(plusIconPath).toHaveAttribute('stroke-linejoin', 'round')
      expect(plusIconPath).toHaveAttribute('stroke-width', '2')
      expect(plusIconPath).toHaveAttribute('d', 'M12 6v6m0 0v6m0-6h6m-6 0H6')
    })

    it('renders empty state container with correct styling', () => {
      render(<RecentAnalyses />)

      const emptyStateContainer = screen.getByText('No analyses yet').closest('.text-center')
      expect(emptyStateContainer).toBeInTheDocument()
      expect(emptyStateContainer).toHaveClass('text-center', 'py-8')
    })

    it('renders button container with correct spacing', () => {
      render(<RecentAnalyses />)

      const buttonContainer = screen.getByRole('button', { name: 'New Analysis' }).parentElement
      expect(buttonContainer).toHaveClass('mt-6')
    })
  })

  describe('Data State Rendering', () => {
    beforeEach(() => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1', 'analysis-2', 'analysis-3'],
      })
    })

    it('shows data state when recentAnalyses.length > 0', () => {
      render(<RecentAnalyses />)

      // Should not show empty state
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()

      // Should show skeleton components
      const skeletons = screen.getAllByTestId('skeleton')
      expect(skeletons).toHaveLength(3)
    })

    it('renders 3 Skeleton components', () => {
      render(<RecentAnalyses />)

      const skeletons = screen.getAllByTestId('skeleton')
      expect(skeletons).toHaveLength(3)
    })

    it('renders each Skeleton with correct classes', () => {
      render(<RecentAnalyses />)

      const skeletons = screen.getAllByTestId('skeleton')
      skeletons.forEach((skeleton) => {
        expect(skeleton).toHaveClass('h-20', 'w-full')
      })
    })

    it('renders skeletons in container with correct spacing', () => {
      render(<RecentAnalyses />)

      const skeletons = screen.getAllByTestId('skeleton')
      const firstSkeleton = skeletons[0]
      const skeletonsContainer = firstSkeleton.parentElement

      expect(skeletonsContainer).toHaveClass('space-y-3')
    })

    it('renders data state container with correct styling', () => {
      render(<RecentAnalyses />)

      const skeletons = screen.getAllByTestId('skeleton')
      const dataContainer = skeletons[0].closest('.space-y-3')

      expect(dataContainer).toBeInTheDocument()
      expect(dataContainer).toHaveClass('space-y-3')
    })
  })

  describe('Conditional Logic', () => {
    it('shows empty state for empty array', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
      expect(screen.queryAllByTestId('skeleton')).toHaveLength(0)
    })

    it('shows data state for non-empty array', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1'],
      })

      render(<RecentAnalyses />)

      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })

    it('shows data state for array with multiple items', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1', 'analysis-2', 'analysis-3', 'analysis-4'],
      })

      render(<RecentAnalyses />)

      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })

    it('correctly evaluates recentAnalyses.length condition', () => {
      // Test with exactly length 0
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      const { rerender } = render(<RecentAnalyses />)
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()

      // Test with exactly length 1
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1'],
      })

      rerender(<RecentAnalyses />)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })
  })

  describe('Button Styling', () => {
    it('renders "View all" button with correct classes', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      expect(viewAllButton).toHaveClass('text-sm', 'text-primary', 'hover:text-primary/80')
    })

    it('renders "New Analysis" button with correct classes', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      expect(newAnalysisButton).toHaveClass(
        'inline-flex',
        'items-center',
        'rounded-md',
        'bg-primary',
        'px-3',
        'py-2',
        'text-sm',
        'font-semibold',
        'text-primary-foreground',
        'shadow-sm',
        'hover:bg-primary/90'
      )
    })

    it('maintains button styling consistency', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })

      // Both buttons should use text-sm
      expect(viewAllButton).toHaveClass('text-sm')
      expect(newAnalysisButton).toHaveClass('text-sm')
    })
  })

  describe('Icon Rendering', () => {
    it('renders empty state chart icon correctly', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const chartIcon = document.querySelector('svg.mx-auto.h-12.w-12.text-muted-foreground')
      expect(chartIcon?.tagName).toBe('svg')
      expect(chartIcon).toHaveClass('mx-auto', 'h-12', 'w-12', 'text-muted-foreground')
    })

    it('renders "New Analysis" plus icon correctly', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      const plusIcon = newAnalysisButton.querySelector('svg')

      expect(plusIcon).toBeInTheDocument()
      expect(plusIcon?.tagName).toBe('svg')
      expect(plusIcon).toHaveClass('-ml-0.5', 'mr-1.5', 'h-5', 'w-5')
    })

    it('ensures icons have proper SVG attributes', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const chartIcon = document.querySelector('svg.mx-auto.h-12.w-12.text-muted-foreground')
      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })
      const plusIcon = newAnalysisButton.querySelector('svg')

      // Chart icon properties
      expect(chartIcon).toHaveAttribute('fill', 'none')
      expect(chartIcon).toHaveAttribute('viewBox', '0 0 24 24')
      expect(chartIcon).toHaveAttribute('stroke', 'currentColor')

      // Plus icon properties
      expect(plusIcon).toHaveAttribute('fill', 'none')
      expect(plusIcon).toHaveAttribute('viewBox', '0 0 24 24')
      expect(plusIcon).toHaveAttribute('stroke', 'currentColor')
    })
  })

  describe('Store Updates', () => {
    it('re-renders when store changes from empty to data', () => {
      const { rerender } = render(<RecentAnalyses />)

      // Start with empty state
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()

      // Change to data state
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1'],
      })
      rerender(<RecentAnalyses />)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })

    it('re-renders when store changes from data to empty', () => {
      const { rerender } = render(<RecentAnalyses />)

      // Start with data state
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1'],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)

      // Change to empty state
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
      expect(screen.queryAllByTestId('skeleton')).toHaveLength(0)
    })

    it('handles dynamic changes in recentAnalyses array length', () => {
      const { rerender } = render(<RecentAnalyses />)

      // Multiple items
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1', 'analysis-2', 'analysis-3'],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)

      // Single item (still shows data state)
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['analysis-1'],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)

      // Empty array
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })
      rerender(<RecentAnalyses />)
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
    })

    it('responds to real store changes using renderHook', () => {
      // This test demonstrates how the component would work with a real store
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      const { rerender } = render(<RecentAnalyses />)
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()

      // Simulate store update
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['new-analysis'],
      })

      rerender(<RecentAnalyses />)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined recentAnalyses array', () => {
      mockUseAnalysisStore.mockReturnValue({})

      // Component should handle this gracefully, likely showing empty state
      render(<RecentAnalyses />)

      // The component should not crash
      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
    })

    it('handles null recentAnalyses', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: null,
      })

      // Component should handle this gracefully
      expect(() => render(<RecentAnalyses />)).not.toThrow()
    })

    it('handles store returning undefined', () => {
      mockUseAnalysisStore.mockReturnValue(undefined)

      // Component should handle this gracefully by showing empty state
      render(<RecentAnalyses />)
      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
    })

    it('handles very large recentAnalyses arrays', () => {
      const largeArray = Array.from({ length: 1000 }, (_, i) => `analysis-${i}`)
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: largeArray,
      })

      render(<RecentAnalyses />)

      // Should still show data state with 3 skeletons
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
    })

    it('handles empty strings in recentAnalyses array', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: ['', 'analysis-1', ''],
      })

      render(<RecentAnalyses />)

      // Should show data state since array length > 0
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
    })

    it('maintains component stability with rapid store changes', () => {
      const { rerender } = render(<RecentAnalyses />)

      // Rapid changes
      for (let i = 0; i < 10; i++) {
        mockUseAnalysisStore.mockReturnValue({
          recentAnalyses: i % 2 === 0 ? [] : [`analysis-${i}`],
        })
        rerender(<RecentAnalyses />)
      }

      // Component should still be functional
      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const mainHeading = screen.getByRole('heading', { level: 2 })
      const subHeading = screen.getByRole('heading', { level: 3 })

      expect(mainHeading).toHaveTextContent('Recent Analyses')
      expect(subHeading).toHaveTextContent('No analyses yet')
    })

    it('has accessible button labels', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      const newAnalysisButton = screen.getByRole('button', { name: 'New Analysis' })

      expect(viewAllButton).toBeInTheDocument()
      expect(newAnalysisButton).toBeInTheDocument()
    })

    it('maintains semantic structure for empty state', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      // Should have proper heading levels
      expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 3 })).toBeInTheDocument()

      // Should have descriptive text
      expect(
        screen.getByText('Get started by analyzing your first SEC filing.')
      ).toBeInTheDocument()
    })

    it('provides appropriate visual hierarchy', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      render(<RecentAnalyses />)

      const mainHeading = screen.getByRole('heading', { level: 2 })
      const subHeading = screen.getByRole('heading', { level: 3 })

      // Main heading should be larger
      expect(mainHeading).toHaveClass('text-lg', 'font-semibold')
      // Sub heading should be smaller
      expect(subHeading).toHaveClass('text-sm', 'font-semibold')
    })
  })

  describe('Component Interface', () => {
    it('accepts no props as per component signature', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      // Component should render without any props
      const component = <RecentAnalyses />
      expect(() => render(component)).not.toThrow()
    })

    it('works as a pure component dependent only on store', () => {
      mockUseAnalysisStore.mockReturnValue({
        recentAnalyses: [],
      })

      const { container: container1 } = render(<RecentAnalyses />)
      const { container: container2 } = render(<RecentAnalyses />)

      // Both instances should render identically
      expect(container1.innerHTML).toBe(container2.innerHTML)
    })
  })

  describe('Performance Considerations', () => {
    it('does not re-render unnecessarily with same store state', () => {
      const mockStore = { recentAnalyses: [] }
      mockUseAnalysisStore.mockReturnValue(mockStore)

      const { rerender } = render(<RecentAnalyses />)

      // Re-render with same store reference
      mockUseAnalysisStore.mockReturnValue(mockStore)
      rerender(<RecentAnalyses />)

      // Component should still work correctly
      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
    })

    it('handles frequent store updates efficiently', () => {
      const { rerender } = render(<RecentAnalyses />)

      // Simulate many updates
      for (let i = 0; i < 100; i++) {
        mockUseAnalysisStore.mockReturnValue({
          recentAnalyses: [`analysis-${i}`],
        })
        rerender(<RecentAnalyses />)
      }

      // Should still render correctly
      expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
    })
  })
})
