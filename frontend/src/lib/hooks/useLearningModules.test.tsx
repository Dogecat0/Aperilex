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
    expect(modules).toHaveLength(2)

    const mdaModule = modules.find((module) => module.moduleKey === 'mda_foundations')
    expect(mdaModule?.context?.analysisId).toBe(latestAnalysisId)
    expect(mdaModule?.title).toBe('MD&A Guided Review')
    expect(mdaModule?.duration).toBe('9 min walkthrough')
    expect(mdaModule?.summary).toContain('Connect commentary')
    expect(mdaModule?.context?.sectionName).toBe('Management Discussion & Analysis')
    expect(mdaModule?.context?.walkthrough?.title).toBe('MD&A Guided Review')
    expect(mdaModule?.context?.guidanceWhyItMatters).toContain('stakeholders')
    expect(mdaModule?.context?.lessonBindings).toHaveLength(2)
    expect(mdaModule?.context?.estimatedDurationMinutes).toBe(9)

    const riskModule = modules.find((module) => module.moduleKey === 'risk_mastery')
    expect(riskModule?.duration).toBe('7 min walkthrough')
    expect(riskModule?.context?.highlight).toContain('Regulators continue probing App Store policies')
    expect(riskModule?.context?.lessonBindings.every((binding) => binding.sectionKey)).toBe(true)
    expect(riskModule?.context?.previousComparison?.pro_tip).toContain('high-severity highlight')
  })
})
