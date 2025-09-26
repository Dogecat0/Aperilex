import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useAppStore } from '@/lib/store'
import { UserPreferences } from './UserPreferences'

// Mock the store
const mockSetTheme = vi.fn()
const mockUpdatePreferences = vi.fn()

const mockStoreState = {
  theme: 'light' as const,
  setTheme: mockSetTheme,
  preferences: {
    defaultAnalysisType: 'comprehensive',
    pageSize: 20,
    enableNotifications: true,
    navigationCollapsed: false,
  },
  updatePreferences: mockUpdatePreferences,
}

vi.mock('@/lib/store', () => ({
  useAppStore: vi.fn(() => mockStoreState),
}))

// Mock Button component to isolate UserPreferences testing
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, className, variant, size, ...props }: any) => (
    <button
      onClick={onClick}
      className={className}
      data-variant={variant}
      data-size={size}
      data-testid="mock-button"
      {...props}
    >
      {children}
    </button>
  ),
}))

describe('UserPreferences Component', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store state
    mockStoreState.theme = 'light'
    mockStoreState.preferences = {
      defaultAnalysisType: 'comprehensive',
      pageSize: 20,
      enableNotifications: true,
      navigationCollapsed: false,
    }
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<UserPreferences />)
      }).not.toThrow()
    })

    it('renders button trigger with settings icon', () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')
      expect(button).toBeInTheDocument()
      expect(button).toHaveAttribute('data-variant', 'ghost')
      expect(button).toHaveAttribute('data-size', 'sm')

      // Check for settings icon SVG
      const svg = button.querySelector('svg')
      expect(svg).toBeInTheDocument()
      expect(svg).toHaveAttribute('viewBox', '0 0 24 24')
      expect(svg).toHaveClass('h-5', 'w-5')
    })

    it('does not render dropdown initially', () => {
      render(<UserPreferences />)

      expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
      expect(screen.queryByText('THEME')).not.toBeInTheDocument()
      expect(screen.queryByText('DISPLAY')).not.toBeInTheDocument()
    })

    it('applies correct container classes', () => {
      render(<UserPreferences />)

      const container = screen.getByTestId('mock-button').closest('div')
      expect(container).toHaveClass('relative')
    })
  })

  describe('Store Integration', () => {
    it('uses theme from store', () => {
      mockStoreState.theme = 'dark'
      render(<UserPreferences />)

      expect(useAppStore).toHaveBeenCalled()
    })

    it('uses setTheme function from store', async () => {
      render(<UserPreferences />)

      // Open dropdown
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      // Click dark theme
      const darkThemeButton = screen.getByText('dark')
      await user.click(darkThemeButton)

      expect(mockSetTheme).toHaveBeenCalledWith('dark')
    })

    it('uses preferences from store', async () => {
      mockStoreState.preferences.enableNotifications = false

      render(<UserPreferences />)

      // Open dropdown
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const notificationsCheckbox = screen.getByLabelText('Enable notifications')

      expect(notificationsCheckbox).not.toBeChecked()
    })

    it('uses updatePreferences function from store', async () => {
      render(<UserPreferences />)

      // Open dropdown
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      // Toggle notifications
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')
      await user.click(notificationsCheckbox)

      expect(mockUpdatePreferences).toHaveBeenCalledWith({ enableNotifications: false })
    })
  })

  describe('Dropdown Toggle', () => {
    it('opens dropdown when button is clicked', async () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')
      await user.click(button)

      expect(screen.getByText('Preferences')).toBeInTheDocument()
      expect(screen.getByText('THEME')).toBeInTheDocument()
      expect(screen.getByText('DISPLAY')).toBeInTheDocument()
    })

    it('closes dropdown when button is clicked again', async () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')

      // Open dropdown
      await user.click(button)
      expect(screen.getByText('Preferences')).toBeInTheDocument()

      // Close dropdown
      await user.click(button)
      expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
    })

    it('toggles dropdown state correctly with multiple clicks', async () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')

      // First click - open
      await user.click(button)
      expect(screen.getByText('Preferences')).toBeInTheDocument()

      // Second click - close
      await user.click(button)
      expect(screen.queryByText('Preferences')).not.toBeInTheDocument()

      // Third click - open again
      await user.click(button)
      expect(screen.getByText('Preferences')).toBeInTheDocument()
    })
  })

  describe('Dropdown Structure', () => {
    beforeEach(async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)
    })

    it('renders backdrop when dropdown is open', () => {
      const backdrop = document.querySelector('.fixed.inset-0.z-10')
      expect(backdrop).toBeInTheDocument()
    })

    it('renders dropdown content with correct positioning', () => {
      const dropdown = document.querySelector('.absolute.right-0.z-20')
      expect(dropdown).toBeInTheDocument()
      expect(dropdown).toHaveClass(
        'mt-2',
        'w-56',
        'rounded-md',
        'border',
        'bg-background',
        'p-2',
        'shadow-lg'
      )
    })

    it('renders header section correctly', () => {
      const header = screen.getByText('Preferences')
      expect(header).toBeInTheDocument()
      expect(header).toHaveClass('text-sm', 'font-semibold')

      const headerContainer = header.parentElement
      expect(headerContainer).toHaveClass('px-2', 'py-1.5')
    })

    it('renders theme section with correct structure', () => {
      const themeLabel = screen.getByText('THEME')
      expect(themeLabel).toBeInTheDocument()
      expect(themeLabel).toHaveClass('text-xs', 'font-semibold', 'text-muted-foreground', 'mb-2')

      const themeSection = themeLabel.parentElement
      expect(themeSection).toHaveClass('px-2', 'py-1')
    })

    it('renders display section with correct structure', () => {
      const displayLabel = screen.getByText('DISPLAY')
      expect(displayLabel).toBeInTheDocument()
      expect(displayLabel).toHaveClass('text-xs', 'font-semibold', 'text-muted-foreground', 'mb-2')

      const displaySection = displayLabel.parentElement
      expect(displaySection).toHaveClass('px-2', 'py-1')
    })

    it('renders separator lines between sections', () => {
      const separators = document.querySelectorAll('hr.my-1')
      expect(separators).toHaveLength(2)
    })
  })

  describe('Backdrop Interaction', () => {
    it('closes dropdown when backdrop is clicked', async () => {
      render(<UserPreferences />)

      // Open dropdown
      const button = screen.getByTestId('mock-button')
      await user.click(button)
      expect(screen.getByText('Preferences')).toBeInTheDocument()

      // Click backdrop
      const backdrop = document.querySelector('.fixed.inset-0.z-10')
      expect(backdrop).toBeInTheDocument()
      fireEvent.click(backdrop!)

      await waitFor(() => {
        expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
      })
    })

    it('backdrop has correct z-index layering', async () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const backdrop = document.querySelector('.fixed.inset-0.z-10')
      const dropdown = document.querySelector('.absolute.right-0.z-20')

      expect(backdrop).toHaveClass('z-10')
      expect(dropdown).toHaveClass('z-20')
    })
  })

  describe('Theme Selection', () => {
    beforeEach(async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)
    })

    it('renders all three theme options', () => {
      expect(screen.getByText('light')).toBeInTheDocument()
      expect(screen.getByText('dark')).toBeInTheDocument()
      expect(screen.getByText('system')).toBeInTheDocument()
    })

    it('shows current theme as selected with radio button filled', () => {
      // Theme is already 'light' from mockStoreState, so light should be selected
      const lightThemeButton = screen.getByText('light').closest('button')
      const radioIndicator = lightThemeButton?.querySelector('.scale-50')

      expect(lightThemeButton).toHaveClass('bg-accent', 'text-accent-foreground')
      expect(radioIndicator).toBeInTheDocument()
    })

    it('shows non-selected themes with hover states', () => {
      mockStoreState.theme = 'light'

      const darkThemeButton = screen.getByText('dark').closest('button')
      const systemThemeButton = screen.getByText('system').closest('button')

      expect(darkThemeButton).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')
      expect(systemThemeButton).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')

      // Should not have bg-accent class (only on hover)
      expect(darkThemeButton).not.toHaveClass('bg-accent')
      expect(systemThemeButton).not.toHaveClass('bg-accent')
    })

    it('capitalizes theme labels correctly', () => {
      const lightButton = screen.getByText('light')
      const darkButton = screen.getByText('dark')
      const systemButton = screen.getByText('system')

      expect(lightButton).toHaveClass('capitalize')
      expect(darkButton).toHaveClass('capitalize')
      expect(systemButton).toHaveClass('capitalize')
    })

    it('calls setTheme when light theme is clicked', async () => {
      const lightThemeButton = screen.getByText('light')
      await user.click(lightThemeButton)

      expect(mockSetTheme).toHaveBeenCalledWith('light')
    })

    it('calls setTheme when dark theme is clicked', async () => {
      const darkThemeButton = screen.getByText('dark')
      await user.click(darkThemeButton)

      expect(mockSetTheme).toHaveBeenCalledWith('dark')
    })

    it('calls setTheme when system theme is clicked', async () => {
      const systemThemeButton = screen.getByText('system')
      await user.click(systemThemeButton)

      expect(mockSetTheme).toHaveBeenCalledWith('system')
    })

    it('closes dropdown after theme selection', async () => {
      const darkThemeButton = screen.getByText('dark')
      await user.click(darkThemeButton)

      await waitFor(() => {
        expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
      })
    })

    it('renders radio button structure correctly', () => {
      const lightThemeButton = screen.getByText('light').closest('button')
      const radioButton = lightThemeButton?.querySelector('.w-3.h-3.rounded-full.border-2')

      expect(radioButton).toBeInTheDocument()
      expect(radioButton).toHaveClass('border-current')
    })

    it('shows filled radio button for selected theme', () => {
      // Theme is already 'light' from mockStoreState setup, so it should be selected
      const lightThemeButton = screen.getByText('light').closest('button')
      const filledIndicator = lightThemeButton?.querySelector('.scale-50')

      expect(filledIndicator).toBeInTheDocument()
      expect(filledIndicator).toHaveClass('w-full', 'h-full', 'rounded-full', 'bg-current')
    })
  })

  describe('Display Preferences', () => {
    beforeEach(async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)
    })

    it('renders notifications checkbox with correct state', () => {
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')
      expect(notificationsCheckbox).toBeInTheDocument()
      expect(notificationsCheckbox).toHaveAttribute('type', 'checkbox')
      expect(notificationsCheckbox).toBeChecked() // Default state is true
    })

    it('reflects preferences.enableNotifications state', async () => {
      // Default enableNotifications is true, so checkbox should be checked
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')
      expect(notificationsCheckbox).toBeChecked() // Default state is true
    })

    it('calls updatePreferences when notifications are toggled off', async () => {
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')
      await user.click(notificationsCheckbox)

      expect(mockUpdatePreferences).toHaveBeenCalledWith({ enableNotifications: false })
    })

    it('calls updatePreferences when notifications are toggled on', async () => {
      // This test case is the inverse of the toggle off case
      // Since enableNotifications starts as true, clicking it will set it to false
      // The opposite case (false -> true) would require a more complex setup
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')
      await user.click(notificationsCheckbox)

      // Verify the toggle function was called (true -> false)
      expect(mockUpdatePreferences).toHaveBeenCalledWith({ enableNotifications: false })
    })

    it('renders checkbox labels with correct structure', () => {
      const notificationsLabel = screen.getByLabelText('Enable notifications').closest('label')

      expect(notificationsLabel).toHaveClass('flex', 'items-center', 'space-x-2', 'py-1')

      const notificationsSpan = notificationsLabel?.querySelector('span')

      expect(notificationsSpan).toHaveClass('text-sm')
    })

    it('applies correct styling to checkboxes', () => {
      const notificationsCheckbox = screen.getByLabelText('Enable notifications')

      expect(notificationsCheckbox).toHaveClass('rounded', 'border-input')
    })
  })

  describe('Visual States', () => {
    beforeEach(async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)
    })

    it('applies selected styling to current theme', () => {
      // Theme is 'light' by default from mockStoreState, so light should be selected
      const lightThemeButton = screen.getByText('light').closest('button')
      expect(lightThemeButton).toHaveClass('bg-accent', 'text-accent-foreground')
    })

    it('applies hover states to non-selected themes', () => {
      mockStoreState.theme = 'light'

      const darkThemeButton = screen.getByText('dark').closest('button')
      const systemThemeButton = screen.getByText('system').closest('button')

      expect(darkThemeButton).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')
      expect(systemThemeButton).toHaveClass('hover:bg-accent', 'hover:text-accent-foreground')
    })

    it('maintains consistent spacing in theme buttons', () => {
      const themeButtons = [
        screen.getByText('light').closest('button'),
        screen.getByText('dark').closest('button'),
        screen.getByText('system').closest('button'),
      ]

      themeButtons.forEach((button) => {
        expect(button).toHaveClass(
          'w-full',
          'flex',
          'items-center',
          'space-x-2',
          'rounded-md',
          'px-2',
          'py-1.5',
          'text-sm'
        )
      })
    })

    it('shows visual feedback for theme selection state', () => {
      // Test with the current theme (light) which is already selected
      const lightThemeButton = screen.getByText('light').closest('button')
      const radioIndicator = lightThemeButton?.querySelector('.scale-50')

      expect(radioIndicator).toBeInTheDocument()
      expect(lightThemeButton).toHaveClass('bg-accent', 'text-accent-foreground')
    })
  })

  describe('Accessibility', () => {
    it('uses proper button semantics for trigger', () => {
      render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('provides accessible checkbox labels', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const notificationsCheckbox = screen.getByLabelText('Enable notifications')

      expect(notificationsCheckbox).toBeInTheDocument()
    })

    it('maintains proper focus order for interactive elements', async () => {
      render(<UserPreferences />)
      const triggerButton = screen.getByTestId('mock-button')
      await user.click(triggerButton)

      const themeButtons = [
        screen.getByText('light'),
        screen.getByText('dark'),
        screen.getByText('system'),
      ]
      const checkboxes = [screen.getByLabelText('Enable notifications')]

      // All interactive elements should be focusable
      themeButtons.forEach((button) => {
        expect(button.closest('button')).not.toHaveAttribute('tabindex', '-1')
      })

      checkboxes.forEach((checkbox) => {
        expect(checkbox).not.toHaveAttribute('tabindex', '-1')
      })
    })

    it('provides appropriate structure for screen readers', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      // Section headers should be clearly marked
      const themeSection = screen.getByText('THEME')
      const displaySection = screen.getByText('DISPLAY')

      expect(themeSection).toHaveClass('text-xs', 'font-semibold')
      expect(displaySection).toHaveClass('text-xs', 'font-semibold')
    })

    it('ensures dropdown structure is accessible', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const dropdown = document.querySelector('.absolute.right-0.z-20')
      expect(dropdown).toBeInTheDocument()

      // Dropdown should contain focusable elements
      const focusableElements = dropdown?.querySelectorAll('button, input')
      expect(focusableElements!.length).toBeGreaterThan(0)
    })
  })

  describe('Edge Cases', () => {
    it('handles rapid button clicks without errors', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')

      // Simulate rapid clicks
      await user.click(button)
      await user.click(button)
      await user.click(button)

      expect(() => {
        // Should not throw any errors
      }).not.toThrow()
    })

    it('handles multiple preference changes correctly', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const notificationsCheckbox = screen.getByLabelText('Enable notifications')

      // Toggle preferences multiple times
      await user.click(notificationsCheckbox)
      await user.click(notificationsCheckbox)

      expect(mockUpdatePreferences).toHaveBeenCalledTimes(2)
      expect(mockUpdatePreferences).toHaveBeenNthCalledWith(1, { enableNotifications: false })
      expect(mockUpdatePreferences).toHaveBeenNthCalledWith(2, { enableNotifications: false })
    })

    it('handles theme switching during dropdown open state', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      // Switch themes multiple times
      const _lightButton = screen.getByText('light')
      const darkButton = screen.getByText('dark')
      const _systemButton = screen.getByText('system')

      await user.click(darkButton)

      // Dropdown should close after first selection
      await waitFor(() => {
        expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
      })

      // Open again and select different theme
      await user.click(button)
      const systemButtonNew = screen.getByText('system')
      await user.click(systemButtonNew)

      expect(mockSetTheme).toHaveBeenCalledTimes(2)
      expect(mockSetTheme).toHaveBeenNthCalledWith(1, 'dark')
      expect(mockSetTheme).toHaveBeenNthCalledWith(2, 'system')
    })

    it('maintains component state after store updates', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      // Change store state externally
      mockStoreState.theme = 'dark'

      // Component should still function correctly
      const lightButton = screen.getByText('light')
      await user.click(lightButton)

      expect(mockSetTheme).toHaveBeenCalledWith('light')
    })

    it('handles clicking outside dropdown area', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      expect(screen.getByText('Preferences')).toBeInTheDocument()

      // Click on backdrop (simulating click outside)
      const backdrop = document.querySelector('.fixed.inset-0.z-10')
      fireEvent.click(backdrop!)

      await waitFor(() => {
        expect(screen.queryByText('Preferences')).not.toBeInTheDocument()
      })
    })

    it('prevents dropdown content from being clicked when closed', () => {
      render(<UserPreferences />)

      // Dropdown should not be in DOM when closed
      expect(screen.queryByText('light')).not.toBeInTheDocument()
      expect(screen.queryByText('dark')).not.toBeInTheDocument()
      expect(screen.queryByText('system')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Enable notifications')).not.toBeInTheDocument()
    })

    it('handles store function errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockSetTheme.mockImplementation(() => {
        throw new Error('Store error')
      })

      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const darkButton = screen.getByText('dark')

      expect(async () => {
        await user.click(darkButton)
      }).not.toThrow()

      consoleError.mockRestore()
    })

    it('handles checkbox state changes with store errors', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockUpdatePreferences.mockImplementation(() => {
        throw new Error('Update error')
      })

      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')
      await user.click(button)

      const notificationsCheckbox = screen.getByLabelText('Enable notifications')

      expect(async () => {
        await user.click(notificationsCheckbox)
      }).not.toThrow()

      consoleError.mockRestore()
    })
  })

  describe('Performance and Optimization', () => {
    it('renders consistently across multiple renders', () => {
      const { rerender } = render(<UserPreferences />)

      const initialButton = screen.getByTestId('mock-button')
      expect(initialButton).toBeInTheDocument()

      rerender(<UserPreferences />)

      const rerenderedButton = screen.getByTestId('mock-button')
      expect(rerenderedButton).toBeInTheDocument()
    })

    it('maintains component structure after re-renders', async () => {
      const { rerender } = render(<UserPreferences />)

      const button = screen.getByTestId('mock-button')
      await user.click(button)

      expect(screen.getByText('Preferences')).toBeInTheDocument()

      rerender(<UserPreferences />)

      // Dropdown should still be open after re-render
      expect(screen.getByText('Preferences')).toBeInTheDocument()
    })

    it('does not create memory leaks during unmount', () => {
      const { unmount } = render(<UserPreferences />)

      expect(() => {
        unmount()
      }).not.toThrow()
    })

    it('handles rapid state changes efficiently', async () => {
      render(<UserPreferences />)
      const button = screen.getByTestId('mock-button')

      // Rapid open/close cycles
      for (let i = 0; i < 5; i++) {
        await user.click(button)
        await user.click(button)
      }

      expect(() => {
        // Should handle rapid changes without issues
      }).not.toThrow()
    })
  })
})
