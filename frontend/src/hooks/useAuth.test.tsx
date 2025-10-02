import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore, resetAuthStoreState } from '@/state/authStore'
import { resetAuthRefreshStateForTests } from '@/state/authSession'
import { useAuth, __resetAuthHydrationForTests } from './useAuth'

class MockBroadcastChannel {
  static channels: MockBroadcastChannel[] = []

  readonly name: string
  private listeners = new Set<(event: MessageEvent) => void>()

  constructor(name: string) {
    this.name = name
    MockBroadcastChannel.channels.push(this)
  }

  postMessage(message: unknown) {
    const targets = MockBroadcastChannel.channels.filter((channel) => channel.name === this.name)
    const event = new MessageEvent('message', { data: message })

    targets.forEach((channel) => {
      channel.listeners.forEach((listener) => listener(event))
    })
  }

  addEventListener(_type: string, listener: (event: MessageEvent) => void) {
    this.listeners.add(listener)
  }

  removeEventListener(_type: string, listener: (event: MessageEvent) => void) {
    this.listeners.delete(listener)
  }

  close() {
    this.listeners.clear()
    MockBroadcastChannel.channels = MockBroadcastChannel.channels.filter(
      (channel) => channel !== this
    )
  }

  static reset() {
    MockBroadcastChannel.channels.splice(0, MockBroadcastChannel.channels.length)
  }
}

async function flushMicrotasks() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('useAuth', () => {
  const originalBroadcastChannel = window.BroadcastChannel
  const originalFetch = window.fetch

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-01T00:00:00.000Z'))
    resetAuthStoreState()
    resetAuthRefreshStateForTests()
    __resetAuthHydrationForTests()
    window.BroadcastChannel = MockBroadcastChannel as unknown as typeof BroadcastChannel
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ message: 'unexpected call' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    )
    window.fetch = fetchMock as unknown as typeof fetch
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    MockBroadcastChannel.reset()
    resetAuthStoreState()
    resetAuthRefreshStateForTests()
    __resetAuthHydrationForTests()
    window.BroadcastChannel = originalBroadcastChannel
    window.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('completes Google callback and stores session', async () => {
    const fetchMock = window.fetch as unknown as ReturnType<typeof vi.fn>

    // Hydration attempt fails with 401 (missing cookie).
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'missing token' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result, unmount } = renderHook(() => useAuth())

    await act(async () => {
      await flushMicrotasks()
    })

    const issuedAt = new Date().toISOString()
    const sessionResponse = {
      accessToken: 'jwt-token',
      tokenType: 'Bearer',
      expiresIn: 180,
      refreshExpiresIn: 3600,
      issuedAt,
      redirectTo: '/dashboard',
      user: {
        id: 'user-42',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: ['analyze:filings'],
      },
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(sessionResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await act(async () => {
      const resultPayload = await result.current.completeCallback({ code: 'code', state: 'state' })
      expect(resultPayload.redirectTo).toBe('/dashboard')
    })

    const state = useAuthStore.getState()
    expect(state.isAuthenticated).toBe(true)
    expect(state.session?.user.email).toBe('investor@example.com')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/google/callback',
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )

    await act(async () => {
      unmount()
    })
  })

  it('schedules refresh and rotates access token before expiry', async () => {
    const fetchMock = window.fetch as unknown as ReturnType<typeof vi.fn>

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'missing token' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result, unmount } = renderHook(() => useAuth())

    await act(async () => {
      await flushMicrotasks()
    })

    const issuedAt = new Date().toISOString()
    const loginPayload = {
      accessToken: 'jwt-token',
      tokenType: 'Bearer',
      expiresIn: 120,
      refreshExpiresIn: 3600,
      issuedAt,
      redirectTo: null,
      user: {
        id: 'user-42',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: [],
      },
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(loginPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await act(async () => {
      await result.current.completeCallback({ code: 'code', state: 'state' })
    })

    const refreshPayload = {
      ...loginPayload,
      accessToken: 'jwt-token-2',
      issuedAt: new Date().toISOString(),
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(refreshPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await act(async () => {
      vi.advanceTimersByTime(60_000)
      await flushMicrotasks()
    })

    const calls = fetchMock.mock.calls
    const refreshCall = calls.find(([url]) => url === '/api/auth/refresh')
    expect(refreshCall).toBeDefined()

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('jwt-token-2')

    await act(async () => {
      unmount()
    })
  })

  it('handles cross-tab logout broadcast', async () => {
    const fetchMock = window.fetch as unknown as ReturnType<typeof vi.fn>

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'missing token' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { result, unmount } = renderHook(() => useAuth())

    await act(async () => {
      await flushMicrotasks()
    })

    const issuedAt = new Date().toISOString()
    const loginPayload = {
      accessToken: 'jwt-token',
      tokenType: 'Bearer',
      expiresIn: 300,
      refreshExpiresIn: 3600,
      issuedAt,
      redirectTo: null,
      user: {
        id: 'user-42',
        email: 'investor@example.com',
        tier: 'BASIC',
        permissions: [],
      },
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(loginPayload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await act(async () => {
      await result.current.completeCallback({ code: 'code', state: 'state' })
    })

    expect(useAuthStore.getState().isAuthenticated).toBe(true)

    const channel = MockBroadcastChannel.channels[0]
    await act(async () => {
      channel.postMessage({ type: 'logout' })
      await flushMicrotasks()
    })

    expect(useAuthStore.getState().isAuthenticated).toBe(false)

    await act(async () => {
      unmount()
    })
  })
})
