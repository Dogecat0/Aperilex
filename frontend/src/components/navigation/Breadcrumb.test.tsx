import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Breadcrumb } from './Breadcrumb'
import type { BreadcrumbItem } from '@/types/navigation'

// Mock the store
const mockUseAppStore = vi.fn()

vi.mock('@/lib/store', () => ({
  useAppStore: () => mockUseAppStore(),
}))

// Test wrapper with Router context
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>{children}</MemoryRouter>
)

describe('Breadcrumb Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing when breadcrumbs exist', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Home', href: '/', isActive: false }],
      })

      expect(() => {
        render(
          <TestWrapper>
            <Breadcrumb />
          </TestWrapper>
        )
      }).not.toThrow()
    })

    it('renders correct nav structure with aria-label', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Home', href: '/', isActive: false }],
      })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav).toBeInTheDocument()
      expect(nav.tagName).toBe('NAV')
      expect(nav).toHaveAttribute('aria-label', 'Breadcrumb')
    })

    it('applies correct CSS classes to nav element', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Home', href: '/', isActive: false }],
      })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav).toHaveClass('mb-4')
    })

    it('renders ordered list with correct structure', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Home', href: '/', isActive: false }],
      })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const list = screen.getByRole('list')
      expect(list).toBeInTheDocument()
      expect(list.tagName).toBe('OL')
      expect(list).toHaveClass(
        'flex',
        'items-center',
        'space-x-2',
        'text-sm',
        'text-muted-foreground'
      )
    })
  })

  describe('Empty State', () => {
    it('returns null when breadcrumbs array is empty', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [],
      })

      const { container } = render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(container.firstChild).toBeNull()
    })

    it('does not render navigation when breadcrumbs length is 0', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [],
      })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
      expect(screen.queryByRole('list')).not.toBeInTheDocument()
    })
  })

  describe('Store Integration', () => {
    it('uses useAppStore to get breadcrumbs', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Test', href: '/test', isActive: false }],
      })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(mockUseAppStore).toHaveBeenCalled()
    })

    it('updates correctly when store breadcrumbs change', () => {
      const initialBreadcrumbs = [{ label: 'Initial', href: '/initial', isActive: false }]
      mockUseAppStore.mockReturnValue({ breadcrumbs: initialBreadcrumbs })

      const { rerender } = render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Initial')).toBeInTheDocument()

      // Update store with new breadcrumbs
      const updatedBreadcrumbs = [{ label: 'Updated', href: '/updated', isActive: false }]
      mockUseAppStore.mockReturnValue({ breadcrumbs: updatedBreadcrumbs })

      rerender(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Updated')).toBeInTheDocument()
      expect(screen.queryByText('Initial')).not.toBeInTheDocument()
    })
  })

  describe('Breadcrumb Items', () => {
    it('renders all breadcrumb items with correct labels', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'Companies', href: '/companies', isActive: false },
        { label: 'Apple Inc.', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Home')).toBeInTheDocument()
      expect(screen.getByText('Companies')).toBeInTheDocument()
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('renders correct number of list items', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'One', href: '/one', isActive: false },
        { label: 'Two', href: '/two', isActive: false },
        { label: 'Three', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(3)
    })

    it('applies correct CSS classes to list items', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Home', href: '/', isActive: false }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const listItem = screen.getByRole('listitem')
      expect(listItem).toHaveClass('flex', 'items-center')
    })
  })

  describe('Links vs Spans', () => {
    it('renders Link for non-active items with href', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'Companies', href: '/companies', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const homeLink = screen.getByRole('link', { name: 'Home' })
      expect(homeLink).toBeInTheDocument()
      expect(homeLink).toHaveAttribute('href', '/')

      const companiesLink = screen.getByRole('link', { name: 'Companies' })
      expect(companiesLink).toBeInTheDocument()
      expect(companiesLink).toHaveAttribute('href', '/companies')
    })

    it('renders span for active items', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'Current Page', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Home should be a link
      expect(screen.getByRole('link', { name: 'Home' })).toBeInTheDocument()

      // Current Page should not be a link
      expect(screen.queryByRole('link', { name: 'Current Page' })).not.toBeInTheDocument()
      expect(screen.getByText('Current Page')).toBeInTheDocument()
    })

    it('renders span for items without href', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'No Link' }, // No href property
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Home should be a link
      expect(screen.getByRole('link', { name: 'Home' })).toBeInTheDocument()

      // No Link should not be a link
      expect(screen.queryByRole('link', { name: 'No Link' })).not.toBeInTheDocument()
      expect(screen.getByText('No Link')).toBeInTheDocument()
    })

    it('renders span for active items even with href', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Active with Href', href: '/active', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Should render as span, not link, because it's active
      expect(screen.queryByRole('link', { name: 'Active with Href' })).not.toBeInTheDocument()
      expect(screen.getByText('Active with Href')).toBeInTheDocument()
    })
  })

  describe('Separators', () => {
    it('renders chevron separators between items', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'Companies', href: '/companies', isActive: false },
        { label: 'Apple Inc.', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Should have 2 separators for 3 items
      const separators = screen.getAllByRole('img', { hidden: true })
      expect(separators).toHaveLength(2)
    })

    it('does not render separator before first item', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Only Item', href: '/', isActive: false }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Should have no separators for single item
      const separators = screen.queryAllByRole('img', { hidden: true })
      expect(separators).toHaveLength(0)
    })

    it('renders correct SVG properties for separators', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'First', href: '/first', isActive: false },
        { label: 'Second', href: '/second', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const container = screen.getByRole('navigation')
      const svgs = container.querySelectorAll('svg')

      expect(svgs).toHaveLength(1) // One separator
      expect(svgs[0]).toHaveClass('mx-2', 'h-4', 'w-4')
      expect(svgs[0]).toHaveAttribute('fill', 'none')
      expect(svgs[0]).toHaveAttribute('viewBox', '0 0 24 24')
      expect(svgs[0]).toHaveAttribute('stroke', 'currentColor')
    })

    it('renders chevron path correctly', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'First', href: '/first', isActive: false },
        { label: 'Second', href: '/second', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const container = screen.getByRole('navigation')
      const path = container.querySelector('path')

      expect(path).toBeInTheDocument()
      expect(path).toHaveAttribute('stroke-linecap', 'round')
      expect(path).toHaveAttribute('stroke-linejoin', 'round')
      expect(path).toHaveAttribute('stroke-width', '2')
      expect(path).toHaveAttribute('d', 'M9 5l7 7-7 7')
    })
  })

  describe('Styling', () => {
    it('applies correct styling to Link elements', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Link Item', href: '/link', isActive: false }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const link = screen.getByRole('link', { name: 'Link Item' })
      expect(link).toHaveClass('hover:text-primary', 'transition-colors')
    })

    it('applies correct styling to active span elements', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Active Item', isActive: true }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const span = screen.getByText('Active Item')
      expect(span.tagName).toBe('SPAN')
      expect(span).toHaveClass('text-foreground', 'font-medium')
    })

    it('applies empty class string to inactive span elements', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Inactive Span' }, // No href, not active
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const span = screen.getByText('Inactive Span')
      expect(span.tagName).toBe('SPAN')
      expect(span).not.toHaveClass('text-foreground', 'font-medium')
    })

    it('maintains hover states for link elements', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Hoverable Link', href: '/hover', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const link = screen.getByRole('link', { name: 'Hoverable Link' })
      expect(link).toHaveClass('hover:text-primary')
    })
  })

  describe('Accessibility', () => {
    it('uses proper semantic navigation element', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Home', href: '/', isActive: false }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav.tagName).toBe('NAV')
      expect(nav).toHaveAttribute('aria-label', 'Breadcrumb')
    })

    it('uses ordered list for proper semantic structure', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'First', href: '/first', isActive: false },
        { label: 'Second', href: '/second', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const list = screen.getByRole('list')
      expect(list.tagName).toBe('OL')

      const listItems = screen.getAllByRole('listitem')
      expect(listItems).toHaveLength(2)
    })

    it('provides proper link semantics', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Accessible Link', href: '/accessible', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const link = screen.getByRole('link', { name: 'Accessible Link' })
      expect(link).toHaveAttribute('href', '/accessible')
      expect(link).toBeVisible()
    })

    it('ensures active items are not focusable as links', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Link', href: '/link', isActive: false },
        { label: 'Active Item', href: '/active', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Regular link should be focusable
      expect(screen.getByRole('link', { name: 'Link' })).toBeInTheDocument()

      // Active item should not be a link
      expect(screen.queryByRole('link', { name: 'Active Item' })).not.toBeInTheDocument()
      expect(screen.getByText('Active Item')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles single breadcrumb correctly', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Single Item', href: '/single', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Single Item')).toBeInTheDocument()
      expect(screen.getAllByRole('listitem')).toHaveLength(1)
      expect(screen.queryAllByRole('img', { hidden: true })).toHaveLength(0) // No separators
    })

    it('handles single active breadcrumb', () => {
      const breadcrumbs: BreadcrumbItem[] = [{ label: 'Active Single', isActive: true }]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const text = screen.getByText('Active Single')
      expect(text.tagName).toBe('SPAN')
      expect(text).toHaveClass('text-foreground', 'font-medium')
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
    })

    it('handles all active breadcrumbs', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Active One', isActive: true },
        { label: 'Active Two', isActive: true },
        { label: 'Active Three', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.queryAllByRole('link')).toHaveLength(0)
      expect(screen.getByText('Active One')).toBeInTheDocument()
      expect(screen.getByText('Active Two')).toBeInTheDocument()
      expect(screen.getByText('Active Three')).toBeInTheDocument()

      // All should have active styling
      const spans = screen.getAllByText(/Active/)
      spans.forEach((span) => {
        expect(span).toHaveClass('text-foreground', 'font-medium')
      })
    })

    it('handles all inactive breadcrumbs with hrefs', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Link One', href: '/one', isActive: false },
        { label: 'Link Two', href: '/two', isActive: false },
        { label: 'Link Three', href: '/three', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getAllByRole('link')).toHaveLength(3)
      expect(screen.getByRole('link', { name: 'Link One' })).toHaveAttribute('href', '/one')
      expect(screen.getByRole('link', { name: 'Link Two' })).toHaveAttribute('href', '/two')
      expect(screen.getByRole('link', { name: 'Link Three' })).toHaveAttribute('href', '/three')
    })

    it('handles breadcrumbs with missing href property', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'With Href', href: '/with-href', isActive: false },
        { label: 'Without Href' }, // Missing href and isActive
        { label: 'Active Without Href', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // First should be a link
      expect(screen.getByRole('link', { name: 'With Href' })).toBeInTheDocument()

      // Second should be a span (no href)
      expect(screen.queryByRole('link', { name: 'Without Href' })).not.toBeInTheDocument()
      expect(screen.getByText('Without Href')).toBeInTheDocument()

      // Third should be a span (active)
      expect(screen.queryByRole('link', { name: 'Active Without Href' })).not.toBeInTheDocument()
      expect(screen.getByText('Active Without Href')).toBeInTheDocument()
    })

    it('handles mixed breadcrumb states correctly', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home', href: '/', isActive: false },
        { label: 'Section' }, // No href, no isActive
        { label: 'Subsection', href: '/subsection', isActive: false },
        { label: 'Current Page', href: '/current', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Home and Subsection should be links
      expect(screen.getByRole('link', { name: 'Home' })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Subsection' })).toBeInTheDocument()

      // Section and Current Page should be spans
      expect(screen.queryByRole('link', { name: 'Section' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Current Page' })).not.toBeInTheDocument()

      // Verify all text is present
      expect(screen.getByText('Home')).toBeInTheDocument()
      expect(screen.getByText('Section')).toBeInTheDocument()
      expect(screen.getByText('Subsection')).toBeInTheDocument()
      expect(screen.getByText('Current Page')).toBeInTheDocument()

      // Verify separators (3 separators for 4 items)
      const separators = screen.getAllByRole('img', { hidden: true })
      expect(separators).toHaveLength(3)
    })

    it('handles store returning undefined breadcrumbs', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: undefined,
      })

      expect(() => {
        render(
          <TestWrapper>
            <Breadcrumb />
          </TestWrapper>
        )
      }).toThrow()
    })

    it('handles empty string labels gracefully', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: '', href: '/', isActive: false },
        { label: 'Valid Label', href: '/valid', isActive: false },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      // Should still render structure
      expect(screen.getAllByRole('listitem')).toHaveLength(2)
      expect(screen.getByText('Valid Label')).toBeInTheDocument()
    })

    it('handles very long breadcrumb paths', () => {
      const breadcrumbs: BreadcrumbItem[] = Array.from({ length: 10 }, (_, i) => ({
        label: `Level ${i + 1}`,
        href: `/level-${i + 1}`,
        isActive: i === 9,
      }))

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getAllByRole('listitem')).toHaveLength(10)
      expect(screen.getAllByRole('link')).toHaveLength(9) // Last one is active
      expect(screen.getAllByRole('img', { hidden: true })).toHaveLength(9) // 9 separators for 10 items
      expect(screen.getByText('Level 10')).toHaveClass('text-foreground', 'font-medium')
    })

    it('handles special characters in breadcrumb labels', () => {
      const breadcrumbs: BreadcrumbItem[] = [
        { label: 'Home & Garden', href: '/home-garden', isActive: false },
        { label: 'Café & Restaurant', href: '/cafe', isActive: false },
        { label: '100% Organic Products', isActive: true },
      ]

      mockUseAppStore.mockReturnValue({ breadcrumbs })

      render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Home & Garden')).toBeInTheDocument()
      expect(screen.getByText('Café & Restaurant')).toBeInTheDocument()
      expect(screen.getByText('100% Organic Products')).toBeInTheDocument()
    })
  })

  describe('Performance and Memory', () => {
    it('re-renders correctly when breadcrumbs change', () => {
      const initialBreadcrumbs = [{ label: 'Initial', href: '/initial', isActive: false }]
      mockUseAppStore.mockReturnValue({ breadcrumbs: initialBreadcrumbs })

      const { rerender } = render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.getByText('Initial')).toBeInTheDocument()

      const newBreadcrumbs = [
        { label: 'First', href: '/first', isActive: false },
        { label: 'Second', isActive: true },
      ]
      mockUseAppStore.mockReturnValue({ breadcrumbs: newBreadcrumbs })

      rerender(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(screen.queryByText('Initial')).not.toBeInTheDocument()
      expect(screen.getByText('First')).toBeInTheDocument()
      expect(screen.getByText('Second')).toBeInTheDocument()
    })

    it('unmounts without errors', () => {
      mockUseAppStore.mockReturnValue({
        breadcrumbs: [{ label: 'Test', href: '/test', isActive: false }],
      })

      const { unmount } = render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    it('maintains consistent DOM structure across renders', () => {
      const breadcrumbs = [{ label: 'Consistent', href: '/consistent', isActive: false }]
      mockUseAppStore.mockReturnValue({ breadcrumbs })

      const { container, rerender } = render(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      const initialHTML = container.innerHTML

      rerender(
        <TestWrapper>
          <Breadcrumb />
        </TestWrapper>
      )

      expect(container.innerHTML).toBe(initialHTML)
    })
  })
})
