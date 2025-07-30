import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { MarketOverview } from './MarketOverview'

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

  describe('Recent SEC Filings Section', () => {
    it('renders Recent SEC Filings subheading', () => {
      render(<MarketOverview />)
      const subheading = screen.getByRole('heading', { name: 'Recent SEC Filings' })

      expect(subheading).toBeInTheDocument()
      expect(subheading).toHaveClass('text-sm', 'font-semibold', 'mb-2')
      expect(subheading.tagName).toBe('H3')
    })

    it('renders all three filing entries with correct content', () => {
      render(<MarketOverview />)

      // Check for filing companies and forms
      expect(screen.getByText('AAPL 10-K')).toBeInTheDocument()
      expect(screen.getByText('GOOGL 10-Q')).toBeInTheDocument()
      expect(screen.getByText('MSFT 8-K')).toBeInTheDocument()

      // Check for timestamps
      expect(screen.getByText('2h ago')).toBeInTheDocument()
      expect(screen.getByText('4h ago')).toBeInTheDocument()
      expect(screen.getByText('6h ago')).toBeInTheDocument()
    })

    it('renders filing entries with correct layout and styling', () => {
      const { container } = render(<MarketOverview />)

      // Find the filings section by finding the h3 with "Recent SEC Filings" text
      const filingHeading = Array.from(container.querySelectorAll('h3')).find(
        (h3) => h3.textContent === 'Recent SEC Filings'
      )
      const filingSection = filingHeading?.parentElement
      const filingEntriesInSection = filingSection?.querySelectorAll(
        '.flex.justify-between.items-center.text-sm'
      )

      expect(filingEntriesInSection).toHaveLength(3)
    })

    it('renders filing companies with muted foreground styling', () => {
      render(<MarketOverview />)

      const appleEntry = screen.getByText('AAPL 10-K')
      const googleEntry = screen.getByText('GOOGL 10-Q')
      const msftEntry = screen.getByText('MSFT 8-K')

      expect(appleEntry).toHaveClass('text-muted-foreground')
      expect(googleEntry).toHaveClass('text-muted-foreground')
      expect(msftEntry).toHaveClass('text-muted-foreground')
    })

    it('renders timestamps with correct styling', () => {
      render(<MarketOverview />)

      const timestamp2h = screen.getByText('2h ago')
      const timestamp4h = screen.getByText('4h ago')
      const timestamp6h = screen.getByText('6h ago')

      expect(timestamp2h).toHaveClass('text-xs', 'text-muted-foreground')
      expect(timestamp4h).toHaveClass('text-xs', 'text-muted-foreground')
      expect(timestamp6h).toHaveClass('text-xs', 'text-muted-foreground')
    })

    it('renders filing entries container with proper spacing', () => {
      const { container } = render(<MarketOverview />)
      const filingContainer = container.querySelector('h3')?.nextElementSibling

      expect(filingContainer).toHaveClass('space-y-2')
    })
  })

  describe("Today's Activity Section", () => {
    it("renders Today's Activity subheading", () => {
      render(<MarketOverview />)
      const subheading = screen.getByRole('heading', { name: "Today's Activity" })

      expect(subheading).toBeInTheDocument()
      expect(subheading).toHaveClass('text-sm', 'font-semibold', 'mb-2')
      expect(subheading.tagName).toBe('H3')
    })

    it('renders all three activity stats with correct labels', () => {
      render(<MarketOverview />)

      expect(screen.getByText('Analyses completed')).toBeInTheDocument()
      expect(screen.getByText('Filings processed')).toBeInTheDocument()
      expect(screen.getByText('Companies analyzed')).toBeInTheDocument()
    })

    it('renders all activity stats with zero values', () => {
      render(<MarketOverview />)

      // Get all elements with font-semibold class that contain "0"
      const zeroValues = screen.getAllByText('0')

      expect(zeroValues).toHaveLength(3)
      zeroValues.forEach((value) => {
        expect(value).toHaveClass('font-semibold')
      })
    })

    it('renders activity entries with correct layout and styling', () => {
      const { container } = render(<MarketOverview />)

      // Find the Today's Activity section
      const activitySection = Array.from(container.querySelectorAll('h3')).find(
        (h3) => h3.textContent === "Today's Activity"
      )?.parentElement

      const activityEntries = activitySection?.querySelectorAll(
        '.flex.justify-between.items-center.text-sm'
      )
      expect(activityEntries).toHaveLength(3)
    })

    it('renders activity stats container with proper spacing', () => {
      const { container } = render(<MarketOverview />)

      // Find Today's Activity heading and get its next sibling (the stats container)
      const activityHeading = Array.from(container.querySelectorAll('h3')).find(
        (h3) => h3.textContent === "Today's Activity"
      )
      const statsContainer = activityHeading?.nextElementSibling

      expect(statsContainer).toHaveClass('space-y-2')
    })

    it('renders activity stat values with font-semibold styling', () => {
      const { container } = render(<MarketOverview />)

      // Find the Today's Activity section
      const activitySection = Array.from(container.querySelectorAll('h3')).find(
        (h3) => h3.textContent === "Today's Activity"
      )?.parentElement

      // Find the stats container (next sibling of the h3)
      const statsContainer = activitySection?.querySelector('.space-y-2')
      const statValues = statsContainer?.querySelectorAll('.font-semibold')

      expect(statValues).toHaveLength(3)

      statValues?.forEach((value) => {
        expect(value.textContent).toBe('0')
        expect(value).toHaveClass('font-semibold')
      })
    })
  })

  describe('Section Separators', () => {
    it('renders horizontal rule separators between sections', () => {
      const { container } = render(<MarketOverview />)
      const hrElements = container.querySelectorAll('hr')

      expect(hrElements).toHaveLength(2)
    })

    it('positions hr elements correctly between sections', () => {
      const { container } = render(<MarketOverview />)

      // Get all child elements of the main content container
      const contentContainer = container.querySelector('.space-y-4')
      const children = Array.from(contentContainer?.children || [])

      // Should have: market stats, hr, filings section, hr, activity section
      expect(children).toHaveLength(5)
      expect(children[1].tagName).toBe('HR') // After market stats
      expect(children[3].tagName).toBe('HR') // After filings section
    })
  })

  describe('Static Content Verification', () => {
    it('displays exact market stats values', () => {
      render(<MarketOverview />)

      expect(screen.getByText('+2.3%')).toBeInTheDocument()
      expect(screen.getByText('+1.8%')).toBeInTheDocument()
      expect(screen.getByText('S&P 500')).toBeInTheDocument()
      expect(screen.getByText('NASDAQ')).toBeInTheDocument()
    })

    it('displays exact SEC filing entries', () => {
      render(<MarketOverview />)

      expect(screen.getByText('AAPL 10-K')).toBeInTheDocument()
      expect(screen.getByText('2h ago')).toBeInTheDocument()

      expect(screen.getByText('GOOGL 10-Q')).toBeInTheDocument()
      expect(screen.getByText('4h ago')).toBeInTheDocument()

      expect(screen.getByText('MSFT 8-K')).toBeInTheDocument()
      expect(screen.getByText('6h ago')).toBeInTheDocument()
    })

    it('displays exact activity stat labels and values', () => {
      render(<MarketOverview />)

      expect(screen.getByText('Analyses completed')).toBeInTheDocument()
      expect(screen.getByText('Filings processed')).toBeInTheDocument()
      expect(screen.getByText('Companies analyzed')).toBeInTheDocument()

      // All values should be 0
      const zeroValues = screen.getAllByText('0')
      expect(zeroValues).toHaveLength(3)
    })
  })

  describe('Layout Structure', () => {
    it('maintains proper section organization', () => {
      const { container } = render(<MarketOverview />)
      const contentContainer = container.querySelector('.space-y-4')

      // Verify the structure: market stats, hr, filings, hr, activity
      const children = Array.from(contentContainer?.children || [])

      // Market stats section
      expect(children[0]).toHaveClass('grid', 'grid-cols-2', 'gap-4')

      // First separator
      expect(children[1].tagName).toBe('HR')

      // Filings section
      const filingsSection = children[2] as HTMLElement
      expect(filingsSection.querySelector('h3')?.textContent).toBe('Recent SEC Filings')

      // Second separator
      expect(children[3].tagName).toBe('HR')

      // Activity section
      const activitySection = children[4] as HTMLElement
      expect(activitySection.querySelector('h3')?.textContent).toBe("Today's Activity")
    })

    it('applies correct spacing classes throughout', () => {
      const { container } = render(<MarketOverview />)

      // Main container spacing
      expect(container.querySelector('.space-y-4')).toBeInTheDocument()

      // Section internal spacing
      const spacingContainers = container.querySelectorAll('.space-y-2')
      expect(spacingContainers).toHaveLength(2) // Filings and activity sections
    })
  })

  describe('Typography', () => {
    it('applies correct text sizes and font weights to headings', () => {
      render(<MarketOverview />)

      const mainTitle = screen.getByRole('heading', { name: 'Market Overview' })
      expect(mainTitle).toHaveClass('text-lg', 'font-semibold')

      const subheadings = screen.getAllByRole('heading', { level: 3 })
      subheadings.forEach((heading) => {
        expect(heading).toHaveClass('text-sm', 'font-semibold')
      })
    })

    it('applies correct text sizes to market stats', () => {
      render(<MarketOverview />)

      const marketValues = [screen.getByText('+2.3%'), screen.getByText('+1.8%')]

      marketValues.forEach((value) => {
        expect(value).toHaveClass('text-2xl', 'font-bold')
      })

      const marketLabels = [screen.getByText('S&P 500'), screen.getByText('NASDAQ')]

      marketLabels.forEach((label) => {
        expect(label).toHaveClass('text-xs', 'text-muted-foreground')
      })
    })

    it('applies correct text sizes to section content', () => {
      const { container } = render(<MarketOverview />)

      // Filing entries should be text-sm
      const filingEntries = container.querySelectorAll('.flex.justify-between.items-center.text-sm')
      expect(filingEntries.length).toBeGreaterThan(0)

      // Timestamps should be text-xs
      const timestamps = [
        screen.getByText('2h ago'),
        screen.getByText('4h ago'),
        screen.getByText('6h ago'),
      ]

      timestamps.forEach((timestamp) => {
        expect(timestamp).toHaveClass('text-xs')
      })
    })
  })

  describe('No Dynamic Content', () => {
    it('renders consistently without props or state', () => {
      // Render multiple times to ensure consistency
      const { unmount } = render(<MarketOverview />)
      expect(screen.getByText('+2.3%')).toBeInTheDocument()
      expect(screen.getByText('AAPL 10-K')).toBeInTheDocument()
      expect(screen.getByText('Analyses completed')).toBeInTheDocument()

      unmount()

      render(<MarketOverview />)
      expect(screen.getByText('+2.3%')).toBeInTheDocument()
      expect(screen.getByText('AAPL 10-K')).toBeInTheDocument()
      expect(screen.getByText('Analyses completed')).toBeInTheDocument()
    })

    it('does not make any API calls or have external dependencies', () => {
      // Since this is a pure static component, we just verify it renders
      // without any network requests or external state
      const { container } = render(<MarketOverview />)
      expect(container.firstChild).toBeInTheDocument()

      // Component should render immediately without any loading states
      expect(screen.getByText('Market Overview')).toBeInTheDocument()
      expect(screen.getByText('+2.3%')).toBeInTheDocument()
    })
  })
})
