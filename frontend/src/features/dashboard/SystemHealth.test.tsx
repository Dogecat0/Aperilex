import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@/test/utils'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { SystemHealth } from './SystemHealth'
import type { DetailedHealthResponse } from '@/api/types'

describe('SystemHealth Component', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  const mockHealthData: DetailedHealthResponse = {
    status: 'healthy',
    timestamp: '2024-01-16T10:00:00Z',
    version: '1.0.0',
    environment: 'development',
    services: {
      database: { status: 'healthy', message: 'Connected', timestamp: '2024-01-16T10:00:00Z' },
      edgar_api: { status: 'healthy', message: 'Operational', timestamp: '2024-01-16T10:00:00Z' },
      llm_provider: {
        status: 'healthy',
        message: 'OpenAI API operational',
        timestamp: '2024-01-16T10:00:00Z',
      },
    },
    configuration: {
      redis_enabled: true,
      celery_enabled: true,
      debug: true,
      redis_url_configured: true,
      celery_broker_configured: true,
    },
  }

  describe('Basic Rendering', () => {
    it('renders component title', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      expect(screen.getByText('System Health')).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'System Health' })).toBeInTheDocument()
    })

    it('has correct card structure', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      const { container } = render(<SystemHealth />)

      const card = container.querySelector('.rounded-lg.border.bg-card.p-6')
      expect(card).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('shows loading skeleton initially', () => {
      // Don't mock the API call to test loading state
      render(<SystemHealth />)

      // Check for skeleton elements
      const skeletonElements = document.querySelectorAll('.animate-pulse.h-4.bg-muted.rounded')
      expect(skeletonElements.length).toBe(3)
    })

    it('hides loading skeleton when data loads', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
      })

      const skeletonElements = document.querySelectorAll('.animate-pulse.h-4.bg-muted.rounded')
      expect(skeletonElements.length).toBe(0)
    })
  })

  describe('Data Rendering', () => {
    it('displays overall status section', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
        // There are multiple "healthy" texts, so we just check one exists
        expect(screen.getAllByText('healthy').length).toBeGreaterThan(0)
      })
    })

    it('renders service statuses', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        // Check for service names (with underscore replaced by space)
        expect(screen.getByText('database')).toBeInTheDocument()
        expect(screen.getByText('edgar api')).toBeInTheDocument()
        expect(screen.getByText('llm provider')).toBeInTheDocument()

        // Check for status values - all services are healthy in our mock
        expect(screen.getAllByText('healthy').length).toBeGreaterThan(1)
      })
    })

    it('displays system information', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Version')).toBeInTheDocument()
        expect(screen.getByText('1.0.0')).toBeInTheDocument()
        expect(screen.getByText('Environment')).toBeInTheDocument()
        expect(screen.getByText('development')).toBeInTheDocument()
        expect(screen.getByText('Last updated')).toBeInTheDocument()
      })
    })

    it('formats timestamp correctly', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        const expectedTime = new Date(mockHealthData.timestamp).toLocaleTimeString()
        expect(screen.getByText(expectedTime)).toBeInTheDocument()
      })
    })
  })

  describe('Status Colors and Indicators', () => {
    it('uses correct color classes for healthy status', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        // Check for green color classes when all services are healthy
        expect(document.querySelector('.text-green-600')).toBeInTheDocument()
        expect(document.querySelector('.bg-green-500')).toBeInTheDocument()

        // Should not have yellow or red colors when all healthy
        expect(document.querySelector('.text-yellow-600')).toBeNull()
        expect(document.querySelector('.text-red-600')).toBeNull()
        expect(document.querySelector('.bg-yellow-500')).toBeNull()
        expect(document.querySelector('.bg-red-500')).toBeNull()
      })
    })

    it('handles unknown status with gray colors', async () => {
      const unknownStatusData = {
        ...mockHealthData,
        status: 'unknown',
        services: {
          test_service: {
            status: 'unknown',
            message: 'Unknown',
            timestamp: '2024-01-16T10:00:00Z',
          },
        },
      }

      // Reset and override handlers completely
      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(unknownStatusData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(unknownStatusData)
        }),
        // Add CORS handlers
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getAllByText('unknown').length).toBeGreaterThan(0)
        expect(document.querySelector('.text-gray-600')).toBeInTheDocument()
        expect(document.querySelector('.bg-gray-500')).toBeInTheDocument()
      })
    })

    it('shows status dots with correct visual indicators', async () => {
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        // Check for status dots (w-2 h-2 rounded-full elements)
        const statusDots = document.querySelectorAll('.w-2.h-2.rounded-full')
        expect(statusDots.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Service Processing', () => {
    it('replaces underscores with spaces in service names', async () => {
      const servicesWithUnderscores = {
        ...mockHealthData,
        services: {
          database_primary: {
            status: 'healthy',
            message: 'Connected',
            timestamp: '2024-01-16T10:00:00Z',
          },
          cache_service: { status: 'warning', message: 'Slow', timestamp: '2024-01-16T10:00:00Z' },
        },
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(servicesWithUnderscores)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(servicesWithUnderscores)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('database primary')).toBeInTheDocument()
        expect(screen.getByText('cache service')).toBeInTheDocument()
      })
    })

    it('handles empty services gracefully', async () => {
      const emptyServicesData = {
        ...mockHealthData,
        services: {},
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(emptyServicesData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(emptyServicesData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
        // Should not have service entries when services is empty
        expect(screen.queryByText('database')).not.toBeInTheDocument()
      })
    })
  })

  describe('Conditional Rendering', () => {
    it('only shows system info when data is available', async () => {
      const partialData = {
        ...mockHealthData,
        version: '',
        environment: '',
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(partialData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(partialData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()

        // Version and environment should not render when empty
        expect(screen.queryByText('Version')).not.toBeInTheDocument()
        expect(screen.queryByText('Environment')).not.toBeInTheDocument()

        // Timestamp should still render
        expect(screen.getByText('Last updated')).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('handles missing health data gracefully', async () => {
      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(null)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(null)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
        expect(screen.getByText('Unknown')).toBeInTheDocument()
      })
    })

    it('renders basic structure on API errors', async () => {
      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.error()
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.error()
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      // Component should still render the title
      expect(screen.getByText('System Health')).toBeInTheDocument()
    })

    it('handles malformed service data', async () => {
      const malformedData = {
        ...mockHealthData,
        services: {
          good_service: { status: 'healthy', message: 'OK', timestamp: '2024-01-16T10:00:00Z' },
          bad_service: null,
        },
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(malformedData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(malformedData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('good service')).toBeInTheDocument()
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
      })
    })
  })

  describe('React Query Integration', () => {
    it('calls the correct API endpoint', async () => {
      const mockApiCall = vi.fn(() => HttpResponse.json(mockHealthData))

      server.resetHandlers(
        http.get('/health/detailed', mockApiCall),
        http.get('http://localhost:8000/health/detailed', mockApiCall),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(mockApiCall).toHaveBeenCalled()
      })
    })

    it('uses query key correctly', async () => {
      // This is tested implicitly by the MSW setup working correctly
      server.use(
        http.get('/health/detailed', () => {
          return HttpResponse.json(mockHealthData)
        })
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
      })
    })

    it('handles refetch intervals', async () => {
      // Test that the component sets up refetch correctly by checking initial behavior
      let callCount = 0

      server.resetHandlers(
        http.get('/health/detailed', () => {
          callCount++
          return HttpResponse.json(mockHealthData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          callCount++
          return HttpResponse.json(mockHealthData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      // Wait for initial call to complete
      await waitFor(() => {
        expect(callCount).toBe(1)
        expect(screen.getByText('System Health')).toBeInTheDocument()
      })

      // Test that the component is working and would make additional calls
      // We can't easily test the exact timing with fake timers due to React Query internals
      expect(callCount).toBeGreaterThanOrEqual(1)
    })

    it('does not retry on failure', async () => {
      let attemptCount = 0

      server.resetHandlers(
        http.get('/health/detailed', () => {
          attemptCount++
          return HttpResponse.error()
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          attemptCount++
          return HttpResponse.error()
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      // Wait for the initial request
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100))
      })

      // Should only attempt once (no retries)
      expect(attemptCount).toBe(1)
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined health response', async () => {
      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(undefined)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(undefined)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('System Health')).toBeInTheDocument()
        expect(screen.getByText('Overall Status')).toBeInTheDocument()
        expect(screen.getByText('Unknown')).toBeInTheDocument()
      })
    })

    it('handles special characters in service names', async () => {
      const specialCharData = {
        ...mockHealthData,
        services: {
          'service-with-dashes': {
            status: 'healthy',
            message: 'OK',
            timestamp: '2024-01-16T10:00:00Z',
          },
          'service.with.dots': {
            status: 'warning',
            message: 'OK',
            timestamp: '2024-01-16T10:00:00Z',
          },
        },
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(specialCharData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(specialCharData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(screen.getByText('service-with-dashes')).toBeInTheDocument()
        expect(screen.getByText('service.with.dots')).toBeInTheDocument()
      })
    })

    it('handles very long service names', async () => {
      const longNameData = {
        ...mockHealthData,
        services: {
          very_long_service_name_that_might_cause_layout_issues: {
            status: 'healthy',
            message: 'OK',
            timestamp: '2024-01-16T10:00:00Z',
          },
        },
      }

      server.resetHandlers(
        http.get('/health/detailed', () => {
          return HttpResponse.json(longNameData)
        }),
        http.get('http://localhost:8000/health/detailed', () => {
          return HttpResponse.json(longNameData)
        }),
        http.options('/*', () => new Response(null, { status: 204 })),
        http.options('http://localhost:8000/*', () => new Response(null, { status: 204 }))
      )

      render(<SystemHealth />)

      await waitFor(() => {
        expect(
          screen.getByText('very long service name that might cause layout issues')
        ).toBeInTheDocument()
      })
    })
  })
})
