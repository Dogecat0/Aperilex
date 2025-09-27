import '@testing-library/jest-dom'

// Provide basic polyfills that the app shell expects when running in JSDOM.
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
    dispatchEvent: () => false,
  }),
})

class NoopObserver {
  observe() {}
  disconnect() {}
  unobserve() {}
}

window.IntersectionObserver = NoopObserver as unknown as typeof IntersectionObserver
window.ResizeObserver = NoopObserver as unknown as typeof ResizeObserver

window.scrollTo = () => {}
