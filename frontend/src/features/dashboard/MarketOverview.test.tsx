import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { MarketOverview } from './MarketOverview'

// MarketOverview is a static component that displays placeholder market data.
// Most sections are commented out as they await future implementation.

describe('MarketOverview', () => {
  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      render(<MarketOverview />)
      expect(screen.getByRole('heading', { name: 'Market Overview' })).toBeInTheDocument()
    })

    it('renders with correct card structure', () => {
      const { container } = render(<MarketOverview />)
      const cardElement = container.firstChild as HTMLElement

      expect(cardElement).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })

    it('renders main content container with proper spacing', () => {
      const { container } = render(<MarketOverview />)
      const spaceContainer = container.querySelector('.space-y-4')

      expect(spaceContainer).toBeInTheDocument()
      expect(spaceContainer).toHaveClass('space-y-4')
    })
  })

  describe('Title Section', () => {
    it('renders Market Overview header correctly', () => {
      render(<MarketOverview />)
      const title = screen.getByRole('heading', { name: 'Market Overview' })

      expect(title).toBeInTheDocument()
      expect(title).toHaveClass('text-lg', 'font-semibold', 'mb-4')
      expect(title.tagName).toBe('H2')
    })
  })

  describe('Market Stats Section', () => {
    it('renders 2-column grid layout for market stats', () => {
      const { container } = render(<MarketOverview />)
      const gridContainer = container.querySelector('.grid.grid-cols-2.gap-4')

      expect(gridContainer).toBeInTheDocument()
      expect(gridContainer).toHaveClass('grid', 'grid-cols-2', 'gap-4')
    })

    it('renders S&P 500 stat with correct styling and content', () => {
      render(<MarketOverview />)

      const spValue = screen.getByText('+2.3%')
      const spLabel = screen.getByText('S&P 500')

      expect(spValue).toBeInTheDocument()
      expect(spValue).toHaveClass('text-2xl', 'font-bold', 'text-green-600')

      expect(spLabel).toBeInTheDocument()
      expect(spLabel).toHaveClass('text-xs', 'text-muted-foreground')
    })

    it('renders NASDAQ stat with correct styling and content', () => {
      render(<MarketOverview />)

      const nasdaqValue = screen.getByText('+1.8%')
      const nasdaqLabel = screen.getByText('NASDAQ')

      expect(nasdaqValue).toBeInTheDocument()
      expect(nasdaqValue).toHaveClass('text-2xl', 'font-bold', 'text-blue-600')

      expect(nasdaqLabel).toBeInTheDocument()
      expect(nasdaqLabel).toHaveClass('text-xs', 'text-muted-foreground')
    })

    it('renders both market stats with center text alignment', () => {
      const { container } = render(<MarketOverview />)
      const statContainers = container.querySelectorAll('.text-center')

      expect(statContainers).toHaveLength(2)
      statContainers.forEach((container) => {
        expect(container).toHaveClass('text-center')
      })
    })

    it('displays correct color coding - green for S&P 500, blue for NASDAQ', () => {
      render(<MarketOverview />)

      const spValue = screen.getByText('+2.3%')
      const nasdaqValue = screen.getByText('+1.8%')

      expect(spValue).toHaveClass('text-green-600')
      expect(nasdaqValue).toHaveClass('text-blue-600')
    })
  })

  // Note: The following sections are commented out in the component
  // and await future implementation, so no tests are needed for them yet:
  // - Recent SEC Filings Section
  // - Analysis Stats Section
})
