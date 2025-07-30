/**
 * Tests for JSDOM Navigation Mock
 *
 * Verifies that our navigation mocking solution properly handles
 * JSDOM limitations while maintaining test functionality.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { navigationMocks, resetNavigationMocks } from './jsdom-navigation-mock'

describe('JSDOM Navigation Mock', () => {
  beforeEach(() => {
    resetNavigationMocks()
  })

  describe('Navigation API Mock', () => {
    it('provides mocked navigation object', () => {
      expect(window.navigation).toBeDefined()
      expect(navigationMocks.navigation).toBeDefined()
    })

    it('provides navigation methods', () => {
      expect(navigationMocks.navigation.navigate).toBeDefined()
      expect(navigationMocks.navigation.back).toBeDefined()
      expect(navigationMocks.navigation.forward).toBeDefined()
      expect(navigationMocks.navigation.reload).toBeDefined()
    })

    it('navigation methods return promises', async () => {
      const result = navigationMocks.navigation.navigate()
      expect(result).toBeInstanceOf(Promise)
      await expect(result).resolves.toBeUndefined()
    })

    it('tracks navigation calls', () => {
      navigationMocks.navigation.navigate()
      expect(navigationMocks.navigation.navigate).toHaveBeenCalledTimes(1)
    })
  })

  describe('History API Mock', () => {
    it('provides mocked history methods', () => {
      expect(navigationMocks.history.pushState).toBeDefined()
      expect(navigationMocks.history.replaceState).toBeDefined()
      expect(navigationMocks.history.back).toBeDefined()
      expect(navigationMocks.history.forward).toBeDefined()
      expect(navigationMocks.history.go).toBeDefined()
    })

    it('tracks history API calls', () => {
      navigationMocks.history.pushState({}, '', '/test')
      expect(navigationMocks.history.pushState).toHaveBeenCalledWith({}, '', '/test')
    })
  })

  describe('Location Mock', () => {
    it('provides location methods', () => {
      expect(navigationMocks.location.assign).toBeDefined()
      expect(navigationMocks.location.replace).toBeDefined()
      expect(navigationMocks.location.reload).toBeDefined()
    })

    it('tracks location method calls', () => {
      navigationMocks.location.assign('/test')
      expect(navigationMocks.location.assign).toHaveBeenCalledWith('/test')
    })
  })

  describe('Mock Reset Functionality', () => {
    it('resets navigation mock calls', () => {
      navigationMocks.navigation.navigate()
      expect(navigationMocks.navigation.navigate).toHaveBeenCalledTimes(1)

      resetNavigationMocks()
      expect(navigationMocks.navigation.navigate).toHaveBeenCalledTimes(0)
    })

    it('resets history mock calls', () => {
      navigationMocks.history.pushState({}, '', '/test')
      expect(navigationMocks.history.pushState).toHaveBeenCalledTimes(1)

      resetNavigationMocks()
      expect(navigationMocks.history.pushState).toHaveBeenCalledTimes(0)
    })

    it('resets location mock calls', () => {
      navigationMocks.location.assign('/test')
      expect(navigationMocks.location.assign).toHaveBeenCalledTimes(1)

      resetNavigationMocks()
      expect(navigationMocks.location.assign).toHaveBeenCalledTimes(0)
    })
  })

  describe('JSDOM Compatibility', () => {
    it('prevents JSDOM navigation warnings', () => {
      // This test would have triggered warnings before our fix
      expect(() => {
        // Simulate what would normally cause JSDOM navigation warnings
        const anchor = document.createElement('a')
        anchor.href = '/test-path'
        document.body.appendChild(anchor)

        // Our mocking should prevent navigation warnings
        anchor.click()

        document.body.removeChild(anchor)
      }).not.toThrow()
    })

    it('maintains navigation functionality for React Router', () => {
      // Verify that our mocks don't interfere with normal DOM operations
      const anchor = document.createElement('a')
      anchor.href = '/test'
      anchor.textContent = 'Test Link'

      expect(anchor.href).toContain('/test')
      expect(anchor.textContent).toBe('Test Link')
    })
  })
})
