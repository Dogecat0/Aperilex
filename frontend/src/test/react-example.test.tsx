import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Simple test component
const TestComponent = ({ name }: { name: string }) => {
  return (
    <div>
      <h1>Hello {name}</h1>
      <button>Click me</button>
    </div>
  )
}

// Test wrapper with providers
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('React Component Testing', () => {
  it('renders a component with providers', () => {
    render(
      <TestWrapper>
        <TestComponent name="World" />
      </TestWrapper>
    )

    expect(screen.getByText('Hello World')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('supports jest-dom matchers', () => {
    render(
      <TestWrapper>
        <TestComponent name="Testing" />
      </TestWrapper>
    )

    const button = screen.getByRole('button')
    expect(button).toBeVisible()
    expect(button).toBeInTheDocument()
  })
})
