/**
 * JSDOM Navigation Mock
 *
 * This module provides comprehensive mocking for navigation APIs that are not
 * implemented in JSDOM, preventing "Not implemented: navigation" warnings
 * while maintaining proper test functionality for React Router navigation.
 */

import { vi } from 'vitest'

// Mock the Navigation API that JSDOM doesn't implement
const mockNavigation = {
  navigate: vi.fn(() => Promise.resolve()),
  reload: vi.fn(() => Promise.resolve()),
  back: vi.fn(() => Promise.resolve()),
  forward: vi.fn(() => Promise.resolve()),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  currentEntry: {
    url: 'http://localhost:3000/',
    index: 0,
    key: 'test-key',
    sameDocument: true,
  },
  entries: vi.fn(() => []),
  canGoBack: false,
  canGoForward: false,
}

// Mock window.navigation
Object.defineProperty(window, 'navigation', {
  writable: true,
  configurable: true,
  value: mockNavigation,
})

// Mock location methods that might trigger navigation
const mockLocationMethods = {
  assign: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn(),
}

// Safely mock location methods without redefining
try {
  // Only define if not already present
  if (typeof window.location.assign === 'undefined') {
    window.location.assign = mockLocationMethods.assign
  }
  if (typeof window.location.replace === 'undefined') {
    window.location.replace = mockLocationMethods.replace
  }
  if (typeof window.location.reload === 'undefined') {
    window.location.reload = mockLocationMethods.reload
  }
} catch (error) {
  // Silently handle any errors with location mocking
  console.warn('Could not mock location methods:', error)
}

// Mock History API methods
const mockHistoryMethods = {
  pushState: vi.fn(),
  replaceState: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  go: vi.fn(),
}

Object.defineProperties(window.history, {
  pushState: {
    writable: true,
    configurable: true,
    value: mockHistoryMethods.pushState,
  },
  replaceState: {
    writable: true,
    configurable: true,
    value: mockHistoryMethods.replaceState,
  },
  back: {
    writable: true,
    configurable: true,
    value: mockHistoryMethods.back,
  },
  forward: {
    writable: true,
    configurable: true,
    value: mockHistoryMethods.forward,
  },
  go: {
    writable: true,
    configurable: true,
    value: mockHistoryMethods.go,
  },
})

// Override HTMLAnchorElement click to prevent navigation
const _originalAnchorClick = HTMLAnchorElement.prototype.click
HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
  // Dispatch a click event without triggering navigation
  const event = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
  })

  // Prevent the default navigation behavior
  event.preventDefault = vi.fn()
  this.dispatchEvent(event)
}

// Export mocks for test verification
export const navigationMocks = {
  navigation: mockNavigation,
  location: mockLocationMethods,
  history: mockHistoryMethods,
}

// Utility to reset all navigation mocks
export const resetNavigationMocks = () => {
  Object.values(mockNavigation).forEach((mock) => {
    if (typeof mock === 'function' && 'mockClear' in mock) {
      mock.mockClear()
    }
  })

  Object.values(mockLocationMethods).forEach((mock) => mock.mockClear())
  Object.values(mockHistoryMethods).forEach((mock) => mock.mockClear())
}
