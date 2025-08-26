import { render, screen } from '@/test/utils'
import { AppShell } from '@/components/layout/AppShell'
import { useAppStore } from '@/lib/store'

// Mock the store
vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(),
}))

// Mock child components to isolate AppShell testing
vi.mock('@/components/layout/Header', () => ({
  Header: () => <header data-testid="header">Header</header>,
}))

vi.mock('@/components/layout/MobileNav', () => ({
  MobileNav: () => <nav data-testid="mobile-nav">MobileNav</nav>,
}))

vi.mock('@/components/layout/Footer', () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}))

vi.mock('@/components/navigation/Breadcrumb', () => ({
  Breadcrumb: () => <nav data-testid="breadcrumb">Breadcrumb</nav>,
}))

describe('AppShell', () => {
  const mockStore = {
    mobileNavOpen: false,
  }

  beforeEach(() => {
    vi.mocked(useAppStore).mockReturnValue(mockStore)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders all layout components', () => {
    render(<AppShell />)

    expect(screen.getByTestId('header')).toBeInTheDocument()
    expect(screen.getByTestId('footer')).toBeInTheDocument()
    expect(screen.getByTestId('breadcrumb')).toBeInTheDocument()
  })

  it('has proper layout structure', () => {
    render(<AppShell />)

    // Check for main content area
    const main = screen.getByRole('main')
    expect(main).toBeInTheDocument()
    expect(main).toHaveClass('flex-1')
  })

  it('applies correct main content styling', () => {
    render(<AppShell />)

    const main = screen.getByRole('main')
    expect(main).toHaveClass('lg:ml-0')
    expect(main).toHaveClass('flex-1')
    expect(main).toHaveClass('transition-all')
  })

  it('renders mobile navigation when mobileNavOpen is true', () => {
    vi.mocked(useAppStore).mockReturnValue({
      ...mockStore,
      mobileNavOpen: true,
    })

    render(<AppShell />)

    expect(screen.getByTestId('mobile-nav')).toBeInTheDocument()
  })

  it('does not render mobile navigation when mobileNavOpen is false', () => {
    vi.mocked(useAppStore).mockReturnValue({
      ...mockStore,
      mobileNavOpen: false,
    })

    render(<AppShell />)

    expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument()
  })

  it('has minimum height styling', () => {
    render(<AppShell />)

    const container = screen.getByTestId('header').parentElement
    expect(container).toHaveClass('min-h-screen')
  })

  it('includes router outlet for page content', () => {
    render(<AppShell />)

    // The main content area should exist for router outlet
    const main = screen.getByRole('main')
    expect(main).toBeInTheDocument()
  })
})
