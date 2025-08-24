/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@api': path.resolve(__dirname, './src/api'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@lib': path.resolve(__dirname, './src/lib'),
      '@types': path.resolve(__dirname, './src/types'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Increase timeout to handle test interference when running full suite
    testTimeout: 10000, // 10 seconds instead of default 5 seconds
    // Better test isolation
    isolate: true, // Run tests in isolated environments
    // Suppress JSDOM navigation warnings in console
    onConsoleLog(log: string, type: 'stdout' | 'stderr'): false | void {
      if (type === 'stderr' && log.includes('Not implemented: navigation')) {
        return false
      }
    },
    silent: false,
    css: {
      modules: {
        classNameStrategy: 'non-scoped',
      },
    },
    coverage: {
      enabled: false, // Only enable when --coverage flag is used
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/**',
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/api/generated-types.ts',
        '**/*.d.ts',
        'coverage/**',
        'dist/**',
        'build/**',
      ],
      include: ['src/**/*.{ts,tsx}'],
      all: true,
      reportOnFailure: true, // Generate coverage even when tests fail
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70,
        },
      },
    },
    // Improved test matching patterns
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/', 'dist/', 'coverage/', 'src/api/generated-types.ts'],
    // Mock handling
    server: {
      deps: {
        inline: ['@testing-library/jest-dom'],
      },
    },
  },
})
