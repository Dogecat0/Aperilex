/**
 * Custom JSDOM Environment
 *
 * This extends the default JSDOM environment to suppress navigation warnings
 * that are not relevant for React Router testing.
 */
import type { Environment } from 'vitest'
import { populateGlobal } from 'vitest/environments'

// Extend the default JSDOM environment
export default <Environment>{
  name: 'custom-jsdom',
  transformMode: 'ssr',
  async setup() {
    // Import and setup JSDOM
    const { JSDOM } = await import('jsdom')

    const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'http://localhost:3000',
      pretendToBeVisual: true,
      resources: 'usable',
      runScripts: 'dangerously',
    })

    const { window } = dom

    // Suppress navigation warnings by overriding console methods
    const originalError = window.console.error
    const originalWarn = window.console.warn

    window.console.error = (...args: any[]) => {
      const message = args[0]
      if (typeof message === 'string' && message.includes('Not implemented: navigation')) {
        return
      }
      originalError.apply(window.console, args)
    }

    window.console.warn = (...args: any[]) => {
      const message = args[0]
      if (typeof message === 'string' && message.includes('Not implemented: navigation')) {
        return
      }
      originalWarn.apply(window.console, args)
    }

    // Populate global with window properties
    const globalObj = global as any
    populateGlobal(globalObj, window, {
      bindFunctions: true,
    })

    return {
      teardown() {
        dom.window.close()
      },
    }
  },
}
