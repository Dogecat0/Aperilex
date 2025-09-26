import { describe, it, expect } from 'vitest'

describe('Test Framework Setup', () => {
  it('should run basic tests', () => {
    expect(1 + 1).toBe(2)
  })

  it('should have access to vi globally', () => {
    const mockFn = vi.fn()
    mockFn('test')
    expect(mockFn).toHaveBeenCalledWith('test')
  })

  it('should support async tests', async () => {
    const promise = Promise.resolve('hello')
    const result = await promise
    expect(result).toBe('hello')
  })
})
