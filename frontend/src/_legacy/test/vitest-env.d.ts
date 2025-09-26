/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />

// Vitest global types are available without import
// vi is available globally through vitest/globals

// Extend the global Window interface for test-specific properties
declare global {
  interface Window {
    IntersectionObserver: typeof IntersectionObserver
    ResizeObserver: typeof ResizeObserver
  }
}
