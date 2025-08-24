import React from 'react'
import { render, screen } from '@/test/utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { RecentAnalyses } from './RecentAnalyses'

// Mock the Skeleton component
vi.mock('@/components/ui/Skeleton', () => ({
  Skeleton: ({ className }: { className: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}))

// Mock the AnalysisCard component
vi.mock('@/features/analyses/components/AnalysisCard', () => ({
  AnalysisCard: ({ analysis }: { analysis: any }) => (
    <div data-testid="analysis-card" data-analysis-id={analysis.analysis_id}>
      Analysis: {analysis.analysis_id}
    </div>
  ),
}))

// Mock the useAnalyses hook
const mockUseAnalyses = vi.fn()
vi.mock('@/hooks/useAnalysis', () => ({
  useAnalyses: (params: any) => mockUseAnalyses(params),
}))

// Test wrapper with React Query and Router

describe('RecentAnalyses', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without errors', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      const { container } = render(<RecentAnalyses />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders card structure with correct styling', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      const { container } = render(<RecentAnalyses />)
      const cardElement = container.firstChild as HTMLElement

      expect(cardElement).toHaveClass('rounded-lg', 'border', 'bg-card', 'p-6')
    })
  })

  describe('Hook Integration', () => {
    it('calls useAnalyses with correct parameters', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      expect(mockUseAnalyses).toHaveBeenCalledWith({
        page: 1,
        page_size: 3,
      })
    })

    it('handles loading state correctly', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      })

      render(<RecentAnalyses />)

      // Should show loading skeletons
      const skeletons = screen.getAllByTestId('skeleton')
      expect(skeletons).toHaveLength(3)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
    })

    it('handles error state correctly', () => {
      const mockError = new Error('Failed to fetch analyses')
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: mockError,
      })

      render(<RecentAnalyses />)

      expect(screen.getByText('Error loading recent analyses')).toBeInTheDocument()
      expect(screen.getByText('Failed to fetch analyses')).toBeInTheDocument()
    })
  })

  describe('Header Section', () => {
    it('renders "Recent Analyses" title', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      const title = screen.getByRole('heading', { level: 2 })
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Recent Analyses')
    })

    it('renders "View all" button', () => {
      mockUseAnalyses.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      const viewAllButton = screen.getByRole('button', { name: 'View all' })
      expect(viewAllButton).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no analyses returned', () => {
      mockUseAnalyses.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      expect(screen.getByText('No analyses yet')).toBeInTheDocument()
      expect(
        screen.getByText('Get started by analyzing your first SEC filing.')
      ).toBeInTheDocument()
    })

    it('renders "Find Analysis" button in empty state', () => {
      mockUseAnalyses.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      const findAnalysisButton = screen.getByRole('button', { name: 'Find Analysis' })
      expect(findAnalysisButton).toBeInTheDocument()
    })
  })

  describe('Data State', () => {
    it('renders analysis cards when data is available', () => {
      const mockAnalyses = [{ analysis_id: 'analysis-1' }, { analysis_id: 'analysis-2' }]

      mockUseAnalyses.mockReturnValue({
        data: { items: mockAnalyses },
        isLoading: false,
        error: null,
      })

      render(<RecentAnalyses />)

      const analysisCards = screen.getAllByTestId('analysis-card')
      expect(analysisCards).toHaveLength(2)
      expect(screen.queryByText('No analyses yet')).not.toBeInTheDocument()
    })
  })
})
