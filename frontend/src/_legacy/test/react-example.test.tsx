import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'

// Simple test component
const TestComponent = ({ name }: { name: string }) => {
  return (
    <div>
      <h1>Hello {name}</h1>
      <button>Click me</button>
    </div>
  )
}

describe('React Component Testing', () => {
  it('renders a component with providers', { timeout: 10000 }, () => {
    render(<TestComponent name="World" />)

    expect(screen.getByText('Hello World')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('supports jest-dom matchers', () => {
    render(<TestComponent name="Testing" />)

    const button = screen.getByRole('button')
    expect(button).toBeVisible()
    expect(button).toBeInTheDocument()
  })
})
