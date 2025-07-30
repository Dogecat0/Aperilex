import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QuickActions } from './QuickActions'

// Mock the Button component to focus on QuickActions logic
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, variant, className, ...props }: any) => (
    <button data-testid="mock-button" data-variant={variant} className={className} {...props}>
      {children}
    </button>
  ),
}))

describe('QuickActions', () => {
  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      render(<QuickActions />)
      expect(screen.getByText('Quick Actions')).toBeInTheDocument()
    })

    it('renders the card container with correct structure', () => {
      const { container: _container } = render(<QuickActions />)
      const cardContainer = _container.firstChild as HTMLElement

      expect(cardContainer).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })
  })

  describe('Title', () => {
    it('renders the "Quick Actions" header correctly', () => {
      render(<QuickActions />)
      const header = screen.getByRole('heading', { level: 2 })

      expect(header).toBeInTheDocument()
      expect(header).toHaveTextContent('Quick Actions')
      expect(header).toHaveClass('text-lg', 'font-semibold', 'mb-4')
    })
  })

  describe('Grid Layout', () => {
    it('has responsive grid classes', () => {
      const { container: _container } = render(<QuickActions />)
      const gridContainer = _container.querySelector('.grid')

      expect(gridContainer).toHaveClass(
        'grid',
        'grid-cols-1',
        'sm:grid-cols-2',
        'lg:grid-cols-4',
        'gap-4'
      )
    })

    it('contains exactly 4 buttons in the grid', () => {
      render(<QuickActions />)
      const buttons = screen.getAllByTestId('mock-button')

      expect(buttons).toHaveLength(4)
    })
  })

  describe('Button Structure', () => {
    it('renders all 4 buttons with correct text content', () => {
      render(<QuickActions />)

      expect(screen.getByText('New Analysis')).toBeInTheDocument()
      expect(screen.getByText('Search Companies')).toBeInTheDocument()
      expect(screen.getByText('Import Filing')).toBeInTheDocument()
      expect(screen.getByText('Browse Companies')).toBeInTheDocument()
    })

    it('renders buttons with correct variants', () => {
      render(<QuickActions />)
      const buttons = screen.getAllByTestId('mock-button')

      // First button should be primary (no variant specified)
      expect(buttons[0]).not.toHaveAttribute('data-variant')

      // Other three buttons should be outline variant
      expect(buttons[1]).toHaveAttribute('data-variant', 'outline')
      expect(buttons[2]).toHaveAttribute('data-variant', 'outline')
      expect(buttons[3]).toHaveAttribute('data-variant', 'outline')
    })
  })

  describe('Button Styling', () => {
    it('applies correct styling classes to all buttons', () => {
      render(<QuickActions />)
      const buttons = screen.getAllByTestId('mock-button')

      buttons.forEach((button) => {
        expect(button).toHaveClass('h-auto', 'p-4', 'flex-col', 'space-y-2')
      })
    })
  })

  describe('Icons', () => {
    it('renders SVG icons for each button with correct classes', () => {
      const { container: _container } = render(<QuickActions />)
      const svgIcons = _container.querySelectorAll('svg')

      expect(svgIcons).toHaveLength(4)

      svgIcons.forEach((svg) => {
        expect(svg).toHaveClass('w-6', 'h-6')
        expect(svg).toHaveAttribute('fill', 'none')
        expect(svg).toHaveAttribute('viewBox', '0 0 24 24')
        expect(svg).toHaveAttribute('stroke', 'currentColor')
      })
    })

    it('renders chart-bar icon for New Analysis button', () => {
      const { container: _container } = render(<QuickActions />)
      const newAnalysisButton = screen.getByText('New Analysis').closest('button')
      const chartIcon = newAnalysisButton?.querySelector('svg path')

      expect(chartIcon).toHaveAttribute(
        'd',
        'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
      )
    })

    it('renders magnifying glass icon for Search Companies button', () => {
      const { container: _container } = render(<QuickActions />)
      const searchButton = screen.getByText('Search Companies').closest('button')
      const searchIcon = searchButton?.querySelector('svg path')

      expect(searchIcon).toHaveAttribute('d', 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z')
    })

    it('renders document icon for Import Filing button', () => {
      const { container: _container } = render(<QuickActions />)
      const importButton = screen.getByText('Import Filing').closest('button')
      const documentIcon = importButton?.querySelector('svg path')

      expect(documentIcon).toHaveAttribute(
        'd',
        'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
      )
    })

    it('renders building icon for Browse Companies button', () => {
      const { container: _container } = render(<QuickActions />)
      const browseButton = screen.getByText('Browse Companies').closest('button')
      const buildingIcon = browseButton?.querySelector('svg path')

      expect(buildingIcon).toHaveAttribute(
        'd',
        'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
      )
    })

    it('applies correct stroke properties to all SVG paths', () => {
      const { container: _container } = render(<QuickActions />)
      const svgPaths = _container.querySelectorAll('svg path')

      svgPaths.forEach((path) => {
        expect(path).toHaveAttribute('stroke-linecap', 'round')
        expect(path).toHaveAttribute('stroke-linejoin', 'round')
        expect(path).toHaveAttribute('stroke-width', '2')
      })
    })
  })

  describe('Text Labels', () => {
    it('renders text spans with correct styling for each button', () => {
      const { container: _container } = render(<QuickActions />)
      const textSpans = _container.querySelectorAll('span')

      expect(textSpans).toHaveLength(4)

      textSpans.forEach((span) => {
        expect(span).toHaveClass('text-sm', 'font-medium')
      })
    })

    it('has correct text content for each span', () => {
      const { container: _container } = render(<QuickActions />)
      const textSpans = _container.querySelectorAll('span')

      expect(textSpans[0]).toHaveTextContent('New Analysis')
      expect(textSpans[1]).toHaveTextContent('Search Companies')
      expect(textSpans[2]).toHaveTextContent('Import Filing')
      expect(textSpans[3]).toHaveTextContent('Browse Companies')
    })
  })

  describe('Accessibility', () => {
    it('uses proper button semantics', () => {
      render(<QuickActions />)
      const buttons = screen.getAllByRole('button')

      expect(buttons).toHaveLength(4)

      buttons.forEach((button) => {
        expect(button.tagName).toBe('BUTTON')
      })
    })

    it('provides accessible text for each button', () => {
      render(<QuickActions />)

      expect(screen.getByRole('button', { name: /new analysis/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /search companies/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /import filing/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /browse companies/i })).toBeInTheDocument()
    })

    it('uses currentColor for icon stroke to support theme changes', () => {
      const { container: _container } = render(<QuickActions />)
      const svgIcons = _container.querySelectorAll('svg')

      svgIcons.forEach((svg) => {
        expect(svg).toHaveAttribute('stroke', 'currentColor')
      })
    })
  })

  describe('Static Content Verification', () => {
    it('renders consistent content on multiple renders', () => {
      const { rerender } = render(<QuickActions />)

      const firstRenderButtons = screen.getAllByTestId('mock-button')
      expect(firstRenderButtons).toHaveLength(4)

      rerender(<QuickActions />)

      const secondRenderButtons = screen.getAllByTestId('mock-button')
      expect(secondRenderButtons).toHaveLength(4)

      // Verify same text content
      expect(screen.getByText('New Analysis')).toBeInTheDocument()
      expect(screen.getByText('Search Companies')).toBeInTheDocument()
      expect(screen.getByText('Import Filing')).toBeInTheDocument()
      expect(screen.getByText('Browse Companies')).toBeInTheDocument()
    })

    it('has no props, state, or dynamic behavior', () => {
      const { container: _container } = render(<QuickActions />)

      // Component should render identically regardless of external state
      // This test ensures the component is truly static
      const initialHTML = _container.innerHTML

      // Re-render and verify identical output
      const { container: secondContainer } = render(<QuickActions />)
      expect(secondContainer.innerHTML).toBe(initialHTML)
    })
  })

  describe('Component Structure Integration', () => {
    it('maintains proper parent-child relationships', () => {
      const { container: _container } = render(<QuickActions />)

      // Card container -> Header + Grid
      const cardContainer = _container.firstChild as HTMLElement
      expect(cardContainer.children).toHaveLength(2)

      // Grid container -> 4 Buttons
      const gridContainer = cardContainer.children[1] as HTMLElement
      expect(gridContainer.children).toHaveLength(4)

      // Each button -> SVG + Span
      Array.from(gridContainer.children).forEach((button) => {
        expect(button.children).toHaveLength(2)
        expect(button.children[0].tagName).toBe('svg')
        expect(button.children[1].tagName).toBe('SPAN')
      })
    })

    it('preserves correct hierarchical structure', () => {
      const { container: _container } = render(<QuickActions />)

      // Verify complete structure path for first button
      const cardContainer = _container.firstChild as HTMLElement
      const gridContainer = cardContainer.children[1] as HTMLElement
      const firstButton = gridContainer.children[0] as HTMLElement
      const firstButtonSvg = firstButton.children[0] as HTMLElement
      const firstButtonSpan = firstButton.children[1] as HTMLElement

      expect(firstButtonSvg).toHaveClass('w-6', 'h-6')
      expect(firstButtonSpan).toHaveTextContent('New Analysis')
      expect(firstButtonSpan).toHaveClass('text-sm', 'font-medium')
    })
  })
})
