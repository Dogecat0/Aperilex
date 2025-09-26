import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll } from 'vitest'
import { server } from './mocks/server'
import './jsdom-navigation-mock'

// Suppress JSDOM navigation errors at the source
const originalError = console.error
const originalStderr = process.stderr.write

beforeAll(() => {
  // Override console.error to filter out JSDOM navigation warnings
  console.error = (...args: any[]) => {
    const message = args[0]
    if (typeof message === 'string' && message.includes('Not implemented: navigation')) {
      return
    }
    originalError.apply(console, args)
  }

  // Override stderr to filter out JSDOM navigation warnings
  process.stderr.write = function (chunk: any) {
    const message = typeof chunk === 'string' ? chunk : chunk.toString()
    if (message.includes('Not implemented: navigation')) {
      return true
    }
    return originalStderr.call(process.stderr, chunk)
  }
})

// Enable MSW API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// Reset any runtime request handlers we may add during the tests
afterEach(() => {
  server.resetHandlers()
  cleanup()
})

// Clean up after the tests are finished
afterAll(() => {
  server.close()
  // Restore original console and stderr
  console.error = originalError
  process.stderr.write = originalStderr
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}

  observe() {
    return null
  }

  disconnect() {
    return null
  }

  unobserve() {
    return null
  }
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}

  observe() {
    return null
  }

  disconnect() {
    return null
  }

  unobserve() {
    return null
  }
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock scrollTo
window.scrollTo = () => {}
