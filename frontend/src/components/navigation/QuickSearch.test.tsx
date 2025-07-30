import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useAppStore } from '@/lib/store'
import { QuickSearch } from './QuickSearch'

// Mock the store
const mockToggleQuickSearch = vi.fn()

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => ({
    quickSearchOpen: false,
    toggleQuickSearch: mockToggleQuickSearch,
  })),
}))

// Mock UI components to isolate QuickSearch testing
vi.mock('@/components/ui/Input', () => ({
  Input: ({ value, onChange, autoFocus, placeholder, ...props }: Record<string, unknown>) => {
    // Create input element with explicit boolean autoFocus
    return (
      <input
        value={value || ''}
        onChange={onChange}
        autoFocus={autoFocus === true}
        placeholder={placeholder}
        data-testid="mock-input"
        data-autofocus={autoFocus ? 'true' : 'false'}
        {...props}
      />
    )
  },
}))

vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, disabled, variant, ...props }: Record<string, unknown>) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-variant={variant}
      data-testid="mock-button"
      {...props}
    >
      {children}
    </button>
  ),
}))

describe('QuickSearch Component', () => {
  const mockStore = vi.mocked(useAppStore)

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset to default closed state
    mockStore.mockImplementation(() => ({
      quickSearchOpen: false,
      toggleQuickSearch: mockToggleQuickSearch,
    }))
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Conditional Rendering', () => {
    it('returns null when quickSearchOpen is false', () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: false,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      const { container } = render(<QuickSearch />)
      expect(container.firstChild).toBeNull()
    })

    it('renders modal when quickSearchOpen is true', () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      // Should render backdrop
      const backdrop = document.querySelector(
        '.fixed.inset-0.z-50.bg-background\\/80.backdrop-blur-sm'
      )
      expect(backdrop).toBeInTheDocument()

      // Should render modal dialog
      const modal = document.querySelector('.fixed.left-\\[50\\%\\].top-\\[50\\%\\]')
      expect(modal).toBeInTheDocument()
    })

    it('handles store state changes correctly', () => {
      const { rerender } = render(<QuickSearch />)

      // Initially closed
      expect(document.querySelector('.fixed.inset-0')).not.toBeInTheDocument()

      // Open modal
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      rerender(<QuickSearch />)
      expect(document.querySelector('.fixed.inset-0')).toBeInTheDocument()

      // Close modal
      mockStore.mockImplementation(() => ({
        quickSearchOpen: false,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      rerender(<QuickSearch />)
      expect(document.querySelector('.fixed.inset-0')).not.toBeInTheDocument()
    })
  })

  describe('Store Integration', () => {
    it('uses quickSearchOpen state from store', () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      expect(useAppStore).toHaveBeenCalled()
      expect(document.querySelector('.fixed.inset-0')).toBeInTheDocument()
    })

    it('uses toggleQuickSearch action from store', () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('accesses store functions correctly on component mount', () => {
      render(<QuickSearch />)

      expect(useAppStore).toHaveBeenCalled()
    })
  })

  describe('Keyboard Shortcuts', () => {
    beforeEach(() => {
      // Add event listener spy
      vi.spyOn(document, 'addEventListener')
      vi.spyOn(document, 'removeEventListener')
    })

    it('toggles modal with Cmd+K on Mac', async () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: false,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      const keyEvent = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
      })

      Object.defineProperty(keyEvent, 'preventDefault', {
        value: vi.fn(),
      })

      fireEvent(document, keyEvent)

      expect(keyEvent.preventDefault).toHaveBeenCalled()
      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('toggles modal with Ctrl+K on Windows', async () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: false,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      const keyEvent = new KeyboardEvent('keydown', {
        key: 'k',
        ctrlKey: true,
        bubbles: true,
      })

      Object.defineProperty(keyEvent, 'preventDefault', {
        value: vi.fn(),
      })

      fireEvent(document, keyEvent)

      expect(keyEvent.preventDefault).toHaveBeenCalled()
      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('closes modal with Escape key when open', async () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      fireEvent.keyDown(document, { key: 'Escape' })

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('does not close modal with Escape key when closed', async () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: false,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      render(<QuickSearch />)

      fireEvent.keyDown(document, { key: 'Escape' })

      expect(mockToggleQuickSearch).not.toHaveBeenCalled()
    })

    it('prevents default behavior for Cmd/Ctrl+K shortcuts', async () => {
      render(<QuickSearch />)

      const cmdKEvent = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
      })

      const ctrlKEvent = new KeyboardEvent('keydown', {
        key: 'k',
        ctrlKey: true,
        bubbles: true,
      })

      const preventDefaultSpy = vi.fn()
      Object.defineProperty(cmdKEvent, 'preventDefault', { value: preventDefaultSpy })
      Object.defineProperty(ctrlKEvent, 'preventDefault', { value: preventDefaultSpy })

      fireEvent(document, cmdKEvent)
      fireEvent(document, ctrlKEvent)

      expect(preventDefaultSpy).toHaveBeenCalledTimes(2)
    })

    it('ignores other key combinations', async () => {
      render(<QuickSearch />)

      // Test various key combinations that should be ignored
      fireEvent.keyDown(document, { key: 'k' }) // Just K
      fireEvent.keyDown(document, { key: 'a', metaKey: true }) // Cmd+A
      fireEvent.keyDown(document, { key: 'Enter' }) // Enter
      fireEvent.keyDown(document, { key: 'Space' }) // Space

      expect(mockToggleQuickSearch).not.toHaveBeenCalled()
    })

    it('sets up and cleans up event listeners correctly', () => {
      const { unmount } = render(<QuickSearch />)

      expect(document.addEventListener).toHaveBeenCalledWith('keydown', expect.any(Function))

      unmount()

      expect(document.removeEventListener).toHaveBeenCalledWith('keydown', expect.any(Function))
    })
  })

  describe('Modal Structure', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('renders backdrop with correct classes', () => {
      render(<QuickSearch />)

      const backdrop = document.querySelector(
        '.fixed.inset-0.z-50.bg-background\\/80.backdrop-blur-sm'
      )
      expect(backdrop).toBeInTheDocument()
      expect(backdrop).toHaveClass(
        'fixed',
        'inset-0',
        'z-50',
        'bg-background/80',
        'backdrop-blur-sm'
      )
    })

    it('renders modal dialog with correct positioning and classes', () => {
      render(<QuickSearch />)

      const modal = document.querySelector('.fixed.left-\\[50\\%\\].top-\\[50\\%\\]')
      expect(modal).toBeInTheDocument()
      expect(modal).toHaveClass(
        'fixed',
        'left-[50%]',
        'top-[50%]',
        'z-50',
        'w-full',
        'max-w-lg',
        'translate-x-[-50%]',
        'translate-y-[-50%]',
        'border',
        'bg-background',
        'p-6',
        'shadow-lg',
        'rounded-lg'
      )
    })

    it('has proper z-index layering', () => {
      render(<QuickSearch />)

      const backdrop = document.querySelector('.fixed.inset-0.z-50')
      const modal = document.querySelector('.fixed.left-\\[50\\%\\].top-\\[50\\%\\].z-50')

      expect(backdrop).toHaveClass('z-50')
      expect(modal).toHaveClass('z-50')
    })

    it('renders header section with title and description', () => {
      render(<QuickSearch />)

      const title = screen.getByText('Quick Search')
      expect(title).toBeInTheDocument()
      expect(title.tagName).toBe('H2')
      expect(title).toHaveClass('text-lg', 'font-semibold')

      const description = screen.getByText('Search for companies, filings, or analyses')
      expect(description).toBeInTheDocument()
      expect(description.tagName).toBe('P')
      expect(description).toHaveClass('text-sm', 'text-muted-foreground')
    })

    it('maintains proper layout spacing', () => {
      render(<QuickSearch />)

      // Check main container spacing
      const mainContainer = screen.getByText('Quick Search').closest('.space-y-4')
      expect(mainContainer).toHaveClass('space-y-4')

      // Check header spacing
      const headerContainer = screen.getByText('Quick Search').closest('.space-y-2')
      expect(headerContainer).toHaveClass('space-y-2')
    })
  })

  describe('Backdrop Interaction', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('closes modal when backdrop is clicked', () => {
      render(<QuickSearch />)

      const backdrop = document.querySelector(
        '.fixed.inset-0.z-50.bg-background\\/80.backdrop-blur-sm'
      )
      expect(backdrop).toBeInTheDocument()

      fireEvent.click(backdrop!)

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('does not close modal when clicking inside modal content', () => {
      render(<QuickSearch />)

      const modal = document.querySelector('.fixed.left-\\[50\\%\\].top-\\[50\\%\\]')
      expect(modal).toBeInTheDocument()

      fireEvent.click(modal!)

      expect(mockToggleQuickSearch).not.toHaveBeenCalled()
    })

    it('handles rapid backdrop clicks correctly', () => {
      render(<QuickSearch />)

      const backdrop = document.querySelector(
        '.fixed.inset-0.z-50.bg-background\\/80.backdrop-blur-sm'
      )

      // Simulate rapid clicks
      fireEvent.click(backdrop!)
      fireEvent.click(backdrop!)
      fireEvent.click(backdrop!)

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(3)
    })
  })

  describe('Input Handling', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('renders input with correct properties', () => {
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('placeholder', 'Search...')
      expect(input).toHaveAttribute('data-autofocus', 'true')
      expect(input).toHaveValue('')
    })

    it('updates query state when input value changes', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')

      await user.type(input, 'AAPL')

      expect(input).toHaveValue('AAPL')
    })

    it('maintains input focus on autoFocus', () => {
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      expect(input).toHaveAttribute('data-autofocus', 'true')
    })

    it('handles empty input state correctly', () => {
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      expect(input).toHaveValue('')

      // Search button should be disabled when query is empty
      const searchButton = screen.getByText('Search')
      expect(searchButton).toBeDisabled()
    })

    it('handles input with content correctly', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      await user.type(input, 'Apple')

      expect(input).toHaveValue('Apple')

      // Search button should be enabled when query has content
      const searchButton = screen.getByText('Search')
      expect(searchButton).not.toBeDisabled()
    })
  })

  describe('Button States', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('renders Cancel button with correct properties', () => {
      render(<QuickSearch />)

      const cancelButton = screen.getByText('Cancel')
      expect(cancelButton).toBeInTheDocument()
      expect(cancelButton).toHaveAttribute('data-variant', 'outline')
      expect(cancelButton).not.toBeDisabled()
    })

    it('renders Search button with correct properties when query is empty', () => {
      render(<QuickSearch />)

      const searchButton = screen.getByText('Search')
      expect(searchButton).toBeInTheDocument()
      expect(searchButton).toBeDisabled()
    })

    it('enables Search button when query has content', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByText('Search')

      // Initially disabled
      expect(searchButton).toBeDisabled()

      // Type content
      await user.type(input, 'test')

      // Should be enabled now
      expect(searchButton).not.toBeDisabled()
    })

    it('disables Search button when query becomes empty', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      const searchButton = screen.getByText('Search')

      // Add content
      await user.type(input, 'test')
      expect(searchButton).not.toBeDisabled()

      // Clear content
      await user.clear(input)
      expect(searchButton).toBeDisabled()
    })

    it('Cancel button calls toggleQuickSearch when clicked', () => {
      render(<QuickSearch />)

      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(1)
    })

    it('handles button interactions correctly', () => {
      render(<QuickSearch />)

      const buttons = screen.getAllByTestId('mock-button')
      expect(buttons).toHaveLength(2) // Cancel and Search

      // Cancel button should always be clickable
      const cancelButton = screen.getByText('Cancel')
      expect(() => fireEvent.click(cancelButton)).not.toThrow()

      // Search button should handle clicks even when disabled
      const searchButton = screen.getByText('Search')
      expect(() => fireEvent.click(searchButton)).not.toThrow()
    })
  })

  describe('Content Display', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('displays recent searches when query is empty', () => {
      render(<QuickSearch />)

      const recentSearchesHeader = screen.getByText('RECENT SEARCHES')
      expect(recentSearchesHeader).toBeInTheDocument()
      expect(recentSearchesHeader).toHaveClass('text-xs', 'font-semibold', 'text-muted-foreground')

      const noRecentSearches = screen.getByText('No recent searches')
      expect(noRecentSearches).toBeInTheDocument()
      expect(noRecentSearches).toHaveClass('text-sm', 'text-muted-foreground')
    })

    it('displays search placeholder when query has content', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      await user.type(input, 'AAPL')

      const placeholder = screen.getByText(
        'Search functionality will be implemented in future phases'
      )
      expect(placeholder).toBeInTheDocument()
      expect(placeholder).toHaveClass('text-sm', 'text-muted-foreground')

      // Recent searches should not be displayed
      expect(screen.queryByText('RECENT SEARCHES')).not.toBeInTheDocument()
    })

    it('switches content based on query state', async () => {
      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')

      // Initially shows recent searches
      expect(screen.getByText('RECENT SEARCHES')).toBeInTheDocument()
      expect(
        screen.queryByText('Search functionality will be implemented in future phases')
      ).not.toBeInTheDocument()

      // Add query - should show search placeholder
      await user.type(input, 'test')
      expect(screen.queryByText('RECENT SEARCHES')).not.toBeInTheDocument()
      expect(
        screen.getByText('Search functionality will be implemented in future phases')
      ).toBeInTheDocument()

      // Clear query - should show recent searches again
      await user.clear(input)
      expect(screen.getByText('RECENT SEARCHES')).toBeInTheDocument()
      expect(
        screen.queryByText('Search functionality will be implemented in future phases')
      ).not.toBeInTheDocument()
    })

    it('maintains proper content layout spacing', () => {
      render(<QuickSearch />)

      // Check results area spacing
      const resultsContainer = screen.getByText('RECENT SEARCHES').closest('.space-y-2')
      expect(resultsContainer).toHaveClass('space-y-2')
    })
  })

  describe('Event Cleanup', () => {
    it('removes event listeners on unmount', () => {
      const addEventListenerSpy = vi.spyOn(document, 'addEventListener')
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener')

      const { unmount } = render(<QuickSearch />)

      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function))

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
    })

    it('updates event listeners when dependencies change', () => {
      const addEventListenerSpy = vi.spyOn(document, 'addEventListener')
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener')

      const { rerender } = render(<QuickSearch />)

      // Change quickSearchOpen state to trigger useEffect
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      rerender(<QuickSearch />)

      // Should have removed old listener and added new one
      expect(removeEventListenerSpy).toHaveBeenCalled()
      expect(addEventListenerSpy).toHaveBeenCalled()
    })

    it('does not create memory leaks during rapid state changes', () => {
      const { rerender } = render(<QuickSearch />)

      // Simulate rapid state changes
      for (let i = 0; i < 5; i++) {
        mockStore.mockImplementation(() => ({
          quickSearchOpen: i % 2 === 0,
          toggleQuickSearch: mockToggleQuickSearch,
        }))
        rerender(<QuickSearch />)
      }

      expect(() => {
        rerender(<QuickSearch />)
      }).not.toThrow()
    })
  })

  describe('Accessibility', () => {
    beforeEach(() => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))
    })

    it('uses proper semantic HTML structure', () => {
      render(<QuickSearch />)

      const title = screen.getByText('Quick Search')
      expect(title.tagName).toBe('H2')

      const description = screen.getByText('Search for companies, filings, or analyses')
      expect(description.tagName).toBe('P')
    })

    it('provides proper input accessibility', () => {
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      expect(input).toHaveAttribute('placeholder', 'Search...')
      expect(input).toHaveAttribute('data-autofocus', 'true')
    })

    it('maintains proper button accessibility', () => {
      render(<QuickSearch />)

      const buttons = screen.getAllByTestId('mock-button')
      buttons.forEach((button) => {
        expect(button.tagName).toBe('BUTTON')
      })

      const cancelButton = screen.getByText('Cancel')
      const searchButton = screen.getByText('Search')

      expect(cancelButton).not.toHaveAttribute('tabindex', '-1')
      expect(searchButton).toHaveAttribute('disabled') // Initially disabled
    })

    it('handles modal focus correctly with autoFocus input', () => {
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')
      expect(input).toHaveAttribute('data-autofocus', 'true')
    })

    it('provides appropriate content hierarchy', () => {
      render(<QuickSearch />)

      // Title should be h2
      const title = screen.getByText('Quick Search')
      expect(title.tagName).toBe('H2')

      // Section headers should have appropriate styling
      const recentSearchesHeader = screen.getByText('RECENT SEARCHES')
      expect(recentSearchesHeader).toHaveClass('text-xs', 'font-semibold')
    })
  })

  describe('Performance and Edge Cases', () => {
    it('handles component unmount during keyboard event', () => {
      const { unmount } = render(<QuickSearch />)

      expect(() => {
        unmount()
        fireEvent.keyDown(document, { key: 'Escape' })
      }).not.toThrow()
    })

    it('handles store errors gracefully', () => {
      // Mock store to throw error
      mockStore.mockImplementation(() => {
        throw new Error('Store error')
      })

      expect(() => {
        render(<QuickSearch />)
      }).toThrow('Store error')
    })

    it('handles missing store properties gracefully', () => {
      // Mock store with missing properties
      mockStore.mockImplementation(
        () =>
          ({
            quickSearchOpen: undefined,
            toggleQuickSearch: undefined,
          }) as Record<string, unknown>
      )

      expect(() => {
        render(<QuickSearch />)
      }).not.toThrow()
    })

    it('maintains consistent rendering across multiple renders', () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      const { rerender } = render(<QuickSearch />)

      screen.getByText('Quick Search')
      screen.getByTestId('mock-input')

      rerender(<QuickSearch />)

      const rerenderedTitle = screen.getByText('Quick Search')
      const rerenderedInput = screen.getByTestId('mock-input')

      expect(rerenderedTitle).toBeInTheDocument()
      expect(rerenderedInput).toBeInTheDocument()
    })

    it('handles rapid keyboard events correctly', () => {
      render(<QuickSearch />)

      // Simulate rapid keyboard events
      for (let i = 0; i < 10; i++) {
        fireEvent.keyDown(document, { key: 'k', metaKey: true })
      }

      expect(mockToggleQuickSearch).toHaveBeenCalledTimes(10)
    })

    it('handles query state updates efficiently', async () => {
      mockStore.mockImplementation(() => ({
        quickSearchOpen: true,
        toggleQuickSearch: mockToggleQuickSearch,
      }))

      const user = userEvent.setup()
      render(<QuickSearch />)

      const input = screen.getByTestId('mock-input')

      // Type and delete content rapidly
      await user.type(input, 'test')
      await user.clear(input)
      await user.type(input, 'another')
      await user.clear(input)

      expect(input).toHaveValue('')
      expect(screen.getByText('RECENT SEARCHES')).toBeInTheDocument()
    })
  })
})
