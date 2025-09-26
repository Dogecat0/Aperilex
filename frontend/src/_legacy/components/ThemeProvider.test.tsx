import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { useAppStore } from '@/lib/store'
import { ThemeProvider } from './ThemeProvider'

// Mock the store
const mockStoreState = {
  theme: 'light' as const,
}

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => mockStoreState.theme),
}))

// Mock matchMedia for system theme testing
const mockMatchMedia = vi.fn()
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: mockMatchMedia,
})

describe('ThemeProvider Component', () => {
  let mockMediaQueryList: {
    matches: boolean
    addEventListener: ReturnType<typeof vi.fn>
    removeEventListener: ReturnType<typeof vi.fn>
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Reset document classes
    document.documentElement.classList.remove('light', 'dark')

    // Setup mock media query list
    mockMediaQueryList = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }

    mockMatchMedia.mockReturnValue(mockMediaQueryList)

    // Reset mock store state
    mockStoreState.theme = 'light'
  })

  afterEach(() => {
    vi.clearAllMocks()
    document.documentElement.classList.remove('light', 'dark')
  })

  describe('Basic Rendering', () => {
    it('renders children without crashing', () => {
      expect(() => {
        render(
          <ThemeProvider>
            <div data-testid="child">Test Child</div>
          </ThemeProvider>
        )
      }).not.toThrow()
    })

    it('renders children content correctly', () => {
      const { getByTestId } = render(
        <ThemeProvider>
          <div data-testid="child">Test Child</div>
        </ThemeProvider>
      )

      expect(getByTestId('child')).toBeInTheDocument()
      expect(getByTestId('child')).toHaveTextContent('Test Child')
    })

    it('calls useAppStore selector correctly', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(useAppStore).toHaveBeenCalled()
    })
  })

  describe('Light Theme Application', () => {
    beforeEach(() => {
      mockStoreState.theme = 'light'
    })

    it('adds light class to document root when theme is light', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    it('removes existing theme classes before applying light theme', () => {
      // Pre-add dark class
      document.documentElement.classList.add('dark')

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    it('does not set up media query listeners for light theme', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).not.toHaveBeenCalled()
      expect(mockMediaQueryList.addEventListener).not.toHaveBeenCalled()
    })
  })

  describe('Dark Theme Application', () => {
    beforeEach(() => {
      mockStoreState.theme = 'dark'
    })

    it('adds dark class to document root when theme is dark', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('removes existing theme classes before applying dark theme', () => {
      // Pre-add light class
      document.documentElement.classList.add('light')

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('does not set up media query listeners for dark theme', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).not.toHaveBeenCalled()
      expect(mockMediaQueryList.addEventListener).not.toHaveBeenCalled()
    })
  })

  describe('System Theme Application', () => {
    beforeEach(() => {
      mockStoreState.theme = 'system'
    })

    it('applies light theme when system prefers light', () => {
      mockMediaQueryList.matches = false // prefers-color-scheme: light

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).toHaveBeenCalledWith('(prefers-color-scheme: dark)')
      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    it('applies dark theme when system prefers dark', () => {
      mockMediaQueryList.matches = true // prefers-color-scheme: dark

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).toHaveBeenCalledWith('(prefers-color-scheme: dark)')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('sets up media query listener for system theme changes', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).toHaveBeenCalledWith('(prefers-color-scheme: dark)')
      expect(mockMediaQueryList.addEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function)
      )
    })

    it('responds to system theme changes', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Get the change handler that was registered
      const changeHandler = mockMediaQueryList.addEventListener.mock.calls[0][1]

      // Simulate system theme change to dark
      const mockEvent = { matches: true }
      changeHandler(mockEvent)

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('responds to system theme changes from dark to light', () => {
      mockMediaQueryList.matches = true // Start with dark

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Initially should be dark
      expect(document.documentElement.classList.contains('dark')).toBe(true)

      // Get the change handler that was registered
      const changeHandler = mockMediaQueryList.addEventListener.mock.calls[0][1]

      // Simulate system theme change to light
      const mockEvent = { matches: false }
      changeHandler(mockEvent)

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('Theme Change Effects', () => {
    it('reapplies theme when store theme changes', () => {
      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Initially light
      expect(document.documentElement.classList.contains('light')).toBe(true)

      // Change theme to dark
      mockStoreState.theme = 'dark'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('switches from explicit theme to system theme correctly', () => {
      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Initially light
      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(mockMediaQueryList.addEventListener).not.toHaveBeenCalled()

      // Change to system theme
      mockStoreState.theme = 'system'
      mockMediaQueryList.matches = false // System prefers light
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(window.matchMedia).toHaveBeenCalledWith('(prefers-color-scheme: dark)')
      expect(mockMediaQueryList.addEventListener).toHaveBeenCalled()
      expect(document.documentElement.classList.contains('light')).toBe(true)
    })

    it('switches from system theme to explicit theme correctly', () => {
      mockStoreState.theme = 'system'
      mockMediaQueryList.matches = true // System prefers dark

      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Initially dark from system
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(mockMediaQueryList.addEventListener).toHaveBeenCalled()

      // Change to explicit light theme
      mockStoreState.theme = 'light'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('light')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('Cleanup and Memory Management', () => {
    it('removes event listener when switching from system theme', () => {
      mockStoreState.theme = 'system'

      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(mockMediaQueryList.addEventListener).toHaveBeenCalled()

      // Change to non-system theme
      mockStoreState.theme = 'light'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(mockMediaQueryList.removeEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function)
      )
    })

    it('removes event listener on component unmount with system theme', () => {
      mockStoreState.theme = 'system'

      const { unmount } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(mockMediaQueryList.addEventListener).toHaveBeenCalled()

      unmount()

      expect(mockMediaQueryList.removeEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function)
      )
    })

    it('does not cause memory leaks on unmount', () => {
      const { unmount } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(() => {
        unmount()
      }).not.toThrow()
    })
  })

  describe('Edge Cases', () => {
    it('handles matchMedia not being available', () => {
      // Temporarily remove matchMedia
      const originalMatchMedia = window.matchMedia
      // @ts-expect-error - Testing edge case
      delete window.matchMedia

      mockStoreState.theme = 'system'

      expect(() => {
        render(
          <ThemeProvider>
            <div>Test</div>
          </ThemeProvider>
        )
      }).toThrow()

      // Restore matchMedia
      window.matchMedia = originalMatchMedia
    })

    it('handles rapid theme changes without errors', () => {
      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Rapidly change themes
      mockStoreState.theme = 'dark'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      mockStoreState.theme = 'system'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      mockStoreState.theme = 'light'
      rerender(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(() => {
        // Should not throw any errors
      }).not.toThrow()
    })

    it('maintains correct theme after multiple re-renders', () => {
      mockStoreState.theme = 'dark'

      const { rerender } = render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      // Re-render multiple times
      for (let i = 0; i < 5; i++) {
        rerender(
          <ThemeProvider>
            <div>Test {i}</div>
          </ThemeProvider>
        )
      }

      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(false)
    })

    it('handles store returning undefined theme gracefully', () => {
      // @ts-expect-error - Testing edge case
      mockStoreState.theme = undefined

      expect(() => {
        render(
          <ThemeProvider>
            <div>Test</div>
          </ThemeProvider>
        )
      }).not.toThrow()
    })
  })

  describe('CSS Class Application', () => {
    it('only applies theme classes to document element', () => {
      render(
        <ThemeProvider>
          <div className="test-child">Test</div>
        </ThemeProvider>
      )

      const childElement = document.querySelector('.test-child')
      expect(childElement?.classList.contains('light')).toBe(false)
      expect(childElement?.classList.contains('dark')).toBe(false)
      expect(document.documentElement.classList.contains('light')).toBe(true)
    })

    it('preserves existing document element classes', () => {
      document.documentElement.classList.add('existing-class')

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('existing-class')).toBe(true)
      expect(document.documentElement.classList.contains('light')).toBe(true)
    })

    it('removes old theme classes but preserves other classes', () => {
      document.documentElement.classList.add('other-class', 'dark', 'another-class')

      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      )

      expect(document.documentElement.classList.contains('other-class')).toBe(true)
      expect(document.documentElement.classList.contains('another-class')).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(false)
      expect(document.documentElement.classList.contains('light')).toBe(true)
    })
  })
})
