import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { describe, it, beforeEach, afterEach, expect, vi } from 'vitest'
import { ThemeProvider } from '@/components/ThemeProvider'
import { apiClient } from '@/lib/apiClient'
import { useLearningModules } from './useLearningModules'
import { mockPaginatedAnalysesResponse, mockAnalysisDetail } from '@/test/fixtures/analyses'

const getSpy = vi.spyOn(apiClient, 'get')
const latestAnalysisId = mockPaginatedAnalysesResponse.items[0].analysis_id

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ThemeProvider>
    )
  }
}

describe('useLearningModules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getSpy.mockImplementation(async (path: string) => {
      if (path === '/analyses') {
        return mockPaginatedAnalysesResponse
      }
      if (path === `/analyses/${latestAnalysisId}`) {
        return {
          ...mockAnalysisDetail,
          analysis_id: latestAnalysisId,
          filing_id: mockPaginatedAnalysesResponse.items[0].filing_id,
        }
      }
      throw new Error(`Unexpected GET path: ${path}`)
    })
  })

  afterEach(() => {
    getSpy.mockReset()
  })

  it('derives module context from recent analyses', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useLearningModules(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    const modules = result.current.data ?? []
    expect(modules).toHaveLength(3)

    const mdaModule = modules.find((module) => module.key === 'mda-101')
    expect(mdaModule?.context?.analysisId).toBe(latestAnalysisId)
    expect(mdaModule?.context?.sectionName).toBe('Management Discussion & Analysis')
    expect(mdaModule?.summary).toContain('Margin expansion stems from services mix')
    expect(mdaModule?.context?.walkthrough?.title).toBe('MD&A Guided Review')
    expect(mdaModule?.context?.lessonBindings).toHaveLength(2)
    expect(mdaModule?.context?.lessonBindings[0]?.source).toBe('highlight')

    const riskModule = modules.find((module) => module.key === 'risk-signal')
    expect(riskModule?.context?.highlight).toContain('Regulatory risk persists')
    expect(riskModule?.context?.lessonBindings.every((binding) => binding.sectionKey)).toBe(true)
    expect(riskModule?.context?.previousComparison?.pro_tip).toContain('high-severity highlight')

    const cashflowModule = modules.find((module) => module.key === 'cashflow-insights')
    expect(cashflowModule?.context?.highlight).toContain('Free cash flow softened')
    expect(cashflowModule?.context?.walkthrough).toBeNull()
  })
})
