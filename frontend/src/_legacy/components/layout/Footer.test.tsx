import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Footer } from './Footer'
import type { HealthResponse } from '@/api/types'

// Mock the API module to avoid real network calls
vi.mock('@/api', () => ({
  aperilexApi: {
    health: {
      health: vi.fn(),
    },
  },
}))

// Mock data
const mockHealthResponses = {
  healthy: {
    status: 'healthy',
    version: '1.0.0',
    environment: 'development',
    timestamp: '2024-01-16T10:00:00Z',
  } as HealthResponse,
  unhealthy: {
    status: 'unhealthy',
    version: '1.0.0',
    environment: 'development',
    timestamp: '2024-01-16T10:00:00Z',
  } as HealthResponse,
  production: {
    status: 'healthy',
    version: '2.1.0',
    environment: 'production',
    timestamp: '2024-01-16T10:00:00Z',
  } as HealthResponse,
}

// Test wrapper with Query Client optimized for testing
const createTestWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        refetchInterval: false, // Disable polling in tests
      },
    },
    logger: {
      log: () => {},
      warn: () => {},
      error: () => {},
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('Footer Component', () => {
  let TestWrapper: ReturnType<typeof createTestWrapper>
  let mockHealthFn: ReturnType<typeof vi.fn>

  beforeEach(async () => {
    // Get the mocked function
    const { aperilexApi } = await import('@/api')
    mockHealthFn = aperilexApi.health.health as ReturnType<typeof vi.fn>

    // Reset the mock
    mockHealthFn.mockReset()

    // Create fresh wrapper for each test
    TestWrapper = createTestWrapper()
  })

  afterEach(() => {
    // Reset mocks
    vi.clearAllMocks()
  })

  describe('Basic Structure and Rendering', () => {
    it('renders the footer with basic structure', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      // Check main footer element
      const footer = screen.getByRole('contentinfo')
      expect(footer).toBeInTheDocument()
      expect(footer).toHaveClass('border-t', 'bg-background')

      // Check container structure
      const container = footer.querySelector('.container')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('mx-auto', 'px-4', 'py-4')
    })

    it('renders branding section correctly', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      // Check copyright text
      const copyrightText = screen.getByText(/2024 Aperilex/)
      expect(copyrightText).toBeInTheDocument()
      expect(copyrightText).toHaveClass('text-sm', 'text-muted-foreground')
      expect(copyrightText).toHaveTextContent(
        /2024 Aperilex.*Open-source financial analysis platform/
      )
    })

    it('renders system status section structure', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      // The status section should be present
      const footer = screen.getByRole('contentinfo')
      const statusSection = footer.querySelector('.flex.items-center.space-x-4:last-child')
      expect(statusSection).toBeInTheDocument()
    })
  })

  describe('Responsive Layout', () => {
    it('applies correct responsive classes for layout', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      const footer = screen.getByRole('contentinfo')
      const flexContainer = footer.querySelector('.flex.flex-col.sm\\:flex-row')
      expect(flexContainer).toBeInTheDocument()
      expect(flexContainer).toHaveClass(
        'flex',
        'flex-col',
        'sm:flex-row',
        'justify-between',
        'items-center',
        'space-y-2',
        'sm:space-y-0'
      )
    })

    it('maintains proper spacing classes for responsive behavior', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      const footer = screen.getByRole('contentinfo')

      // Check branding section spacing
      const brandingSection = footer.querySelector('.flex.items-center.space-x-4:first-child')
      expect(brandingSection).toBeInTheDocument()
      expect(brandingSection).toHaveClass('flex', 'items-center', 'space-x-4')

      // Check status section spacing
      const statusSection = footer.querySelector('.flex.items-center.space-x-4:last-child')
      expect(statusSection).toBeInTheDocument()
      expect(statusSection).toHaveClass('flex', 'items-center', 'space-x-4')
    })
  })

  describe('React Query Integration', () => {
    it('queries health endpoint on mount', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      // Wait for the API call to be made
      await waitFor(
        () => {
          expect(mockHealthFn).toHaveBeenCalledTimes(1)
        },
        { timeout: 1000 }
      )
    })

    it('handles API failures gracefully', async () => {
      mockHealthFn.mockRejectedValue(new Error('API Error'))

      render(<Footer />, { wrapper: TestWrapper })

      // Wait for the API call to be made
      await waitFor(
        () => {
          expect(mockHealthFn).toHaveBeenCalledTimes(1)
        },
        { timeout: 1000 }
      )
    })
  })

  describe('API Status Display', () => {
    it('displays healthy status with green indicator', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const statusIndicator = screen.getByText('API healthy')
          expect(statusIndicator).toBeInTheDocument()
          expect(statusIndicator).toHaveClass('text-xs', 'text-muted-foreground')
        },
        { timeout: 1000 }
      )

      // Check for green status dot
      const footer = screen.getByRole('contentinfo')
      const greenDot = footer.querySelector('.bg-green-500')
      expect(greenDot).toBeInTheDocument()
      expect(greenDot).toHaveClass('w-2', 'h-2', 'rounded-full', 'bg-green-500')
    })

    it('displays unhealthy status with red indicator', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.unhealthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const statusIndicator = screen.getByText('API unhealthy')
          expect(statusIndicator).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // Check for red status dot
      const footer = screen.getByRole('contentinfo')
      const redDot = footer.querySelector('.bg-red-500')
      expect(redDot).toBeInTheDocument()
      expect(redDot).toHaveClass('w-2', 'h-2', 'rounded-full', 'bg-red-500')
    })

    it('displays unknown status when health data is unavailable', async () => {
      mockHealthFn.mockRejectedValue(new Error('API Error'))

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const statusIndicator = screen.getByText('API unknown')
          expect(statusIndicator).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // Check for red status dot (default for failed/unknown)
      const footer = screen.getByRole('contentinfo')
      const redDot = footer.querySelector('.bg-red-500')
      expect(redDot).toBeInTheDocument()
    })
  })

  describe('Version Information Display', () => {
    it('displays version when available', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const versionElement = screen.getByText('v1.0.0')
          expect(versionElement).toBeInTheDocument()
          expect(versionElement).toHaveClass('text-xs', 'text-muted-foreground')
        },
        { timeout: 1000 }
      )
    })

    it('does not display version when unavailable', async () => {
      const healthWithoutVersion = {
        status: 'healthy',
        timestamp: '2024-01-16T10:00:00Z',
      } as HealthResponse

      mockHealthFn.mockResolvedValue(healthWithoutVersion)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          expect(screen.getByText('API healthy')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // Version should not be displayed
      expect(screen.queryByText(/^v/)).not.toBeInTheDocument()
    })

    it('formats version number correctly with v prefix', async () => {
      const healthWithCustomVersion = {
        status: 'healthy',
        version: '2.5.3-beta',
        timestamp: '2024-01-16T10:00:00Z',
      } as HealthResponse

      mockHealthFn.mockResolvedValue(healthWithCustomVersion)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const versionElement = screen.getByText('v2.5.3-beta')
          expect(versionElement).toBeInTheDocument()
        },
        { timeout: 1000 }
      )
    })
  })

  describe('Environment Badge Display', () => {
    it('displays environment badge for non-production environments', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const envBadge = screen.getByText('development')
          expect(envBadge).toBeInTheDocument()
          expect(envBadge).toHaveClass(
            'inline-flex',
            'items-center',
            'rounded-full',
            'bg-yellow-100',
            'px-2.5',
            'py-0.5',
            'text-xs',
            'font-medium',
            'text-yellow-800'
          )
        },
        { timeout: 1000 }
      )
    })

    it('does not display environment badge for production', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.production)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          // Version should be displayed
          expect(screen.getByText('v2.1.0')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // Environment badge should not be displayed for production
      expect(screen.queryByText('production')).not.toBeInTheDocument()
    })

    it('displays custom environment names correctly', async () => {
      const healthWithStagingEnv = {
        status: 'healthy',
        version: '1.5.0',
        environment: 'staging',
        timestamp: '2024-01-16T10:00:00Z',
      } as HealthResponse

      mockHealthFn.mockResolvedValue(healthWithStagingEnv)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const envBadge = screen.getByText('staging')
          expect(envBadge).toBeInTheDocument()
          expect(envBadge).toHaveClass('bg-yellow-100', 'text-yellow-800')
        },
        { timeout: 1000 }
      )
    })

    it('does not display environment badge when environment is not provided', async () => {
      const healthWithoutEnv = {
        status: 'healthy',
        version: '1.0.0',
        timestamp: '2024-01-16T10:00:00Z',
      } as HealthResponse

      mockHealthFn.mockResolvedValue(healthWithoutEnv)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          expect(screen.getByText('API healthy')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // No environment badge should be displayed
      const footer = screen.getByRole('contentinfo')
      const envBadge = footer.querySelector('.bg-yellow-100')
      expect(envBadge).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      mockHealthFn.mockRejectedValue(new Error('Network Error'))

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const statusIndicator = screen.getByText('API unknown')
          expect(statusIndicator).toBeInTheDocument()
        },
        { timeout: 1000 }
      )

      // Should show red indicator for errors
      const footer = screen.getByRole('contentinfo')
      const redDot = footer.querySelector('.bg-red-500')
      expect(redDot).toBeInTheDocument()
    })

    it('handles 404 errors gracefully', async () => {
      mockHealthFn.mockRejectedValue(new Error('404 Not Found'))

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          expect(screen.getByText('API unknown')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )
    })

    it('handles 500 errors gracefully', async () => {
      mockHealthFn.mockRejectedValue(new Error('500 Internal Server Error'))

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          expect(screen.getByText('API unknown')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )
    })

    it('handles malformed response gracefully', async () => {
      mockHealthFn.mockRejectedValue(new Error('Invalid JSON'))

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          expect(screen.getByText('API unknown')).toBeInTheDocument()
        },
        { timeout: 1000 }
      )
    })
  })

  describe('Accessibility', () => {
    it('uses semantic footer element', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      const footer = screen.getByRole('contentinfo')
      expect(footer.tagName).toBe('FOOTER')
    })

    it('provides accessible text for status indicator', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const statusText = screen.getByText('API healthy')
          expect(statusText).toBeInTheDocument()
          expect(statusText).toBeVisible()
        },
        { timeout: 1000 }
      )
    })

    it('maintains proper contrast for text elements', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          // Check copyright text has muted styling
          const copyrightText = screen.getByText(/2024 Aperilex/)
          expect(copyrightText).toHaveClass('text-muted-foreground')

          // Check status text has muted styling
          const statusText = screen.getByText('API healthy')
          expect(statusText).toHaveClass('text-muted-foreground')

          // Check version text has muted styling
          const versionText = screen.getByText('v1.0.0')
          expect(versionText).toHaveClass('text-muted-foreground')
        },
        { timeout: 1000 }
      )
    })

    it('provides visible status indicators with appropriate sizing', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          const footer = screen.getByRole('contentinfo')
          const statusDot = footer.querySelector('.w-2.h-2.rounded-full')
          expect(statusDot).toBeInTheDocument()
          expect(statusDot).toHaveClass('w-2', 'h-2', 'rounded-full')
        },
        { timeout: 1000 }
      )
    })

    it('maintains readable text sizing for all elements', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      await waitFor(
        () => {
          // Copyright text should be small but readable
          const copyrightText = screen.getByText(/2024 Aperilex/)
          expect(copyrightText).toHaveClass('text-sm')

          // Status and version text should be extra small but still accessible
          const statusText = screen.getByText('API healthy')
          expect(statusText).toHaveClass('text-xs')

          const versionText = screen.getByText('v1.0.0')
          expect(versionText).toHaveClass('text-xs')
        },
        { timeout: 1000 }
      )
    })
  })

  describe('Component Lifecycle', () => {
    it('starts making health checks immediately on mount', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      render(<Footer />, { wrapper: TestWrapper })

      // Should make request immediately on mount
      await waitFor(
        () => {
          expect(mockHealthFn).toHaveBeenCalledTimes(1)
        },
        { timeout: 1000 }
      )
    })

    it('handles multiple mount/unmount cycles correctly', async () => {
      mockHealthFn.mockResolvedValue(mockHealthResponses.healthy)

      // First mount
      const { unmount: unmount1 } = render(<Footer />, { wrapper: TestWrapper })
      await waitFor(
        () => {
          expect(mockHealthFn).toHaveBeenCalledTimes(1)
        },
        { timeout: 1000 }
      )
      unmount1()

      // Second mount with fresh wrapper
      const FreshTestWrapper = createTestWrapper()
      const { unmount: unmount2 } = render(<Footer />, { wrapper: FreshTestWrapper })
      await waitFor(
        () => {
          expect(mockHealthFn).toHaveBeenCalledTimes(2)
        },
        { timeout: 1000 }
      )
      unmount2()
    })
  })
})
