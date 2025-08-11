import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@/test/utils'
import { FilingAnalysisSection } from './FilingAnalysisSection'
import type { AnalysisResponse, AnalysisProgress } from '@/api/types'

describe('FilingAnalysisSection Progressive Loading', () => {
  const mockAnalysis: AnalysisResponse = {
    analysis_id: 'test-analysis-id',
    filing_id: 'test-filing-id',
    analysis_template: 'comprehensive',
    created_by: 'test-user',
    created_at: '2024-01-16T10:00:00Z',
    confidence_score: 0.85,
    llm_provider: 'openai',
    llm_model: 'gpt-4',
    processing_time_seconds: 45,
    filing_summary: 'Test filing summary',
    executive_summary: 'Test executive summary',
    key_insights: ['Insight 1', 'Insight 2'],
    risk_factors: ['Risk 1', 'Risk 2'],
    opportunities: ['Opportunity 1'],
    financial_highlights: ['Highlight 1'],
    sections_analyzed: 5,
  }

  describe('Progressive Loading States', () => {
    it('shows initiating state correctly', () => {
      const progressData: AnalysisProgress = {
        state: 'initiating',
        message: 'Initiating analysis...',
        progress_percent: 0,
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Initiating analysis...')).toBeInTheDocument()
      expect(screen.getByText('Analysis Results')).toBeInTheDocument()

      // Check for spinning icon
      const spinningIcon = document.querySelector('.animate-spin')
      expect(spinningIcon).toBeInTheDocument()
    })

    it('shows loading filing state with appropriate icon', () => {
      const progressData: AnalysisProgress = {
        state: 'loading_filing',
        message: 'Loading filing data...',
        progress_percent: 25,
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Loading filing data...')).toBeInTheDocument()

      // Check for progress bar
      const progressBar = document.querySelector('.bg-blue-600')
      expect(progressBar).toBeInTheDocument()
      expect(progressBar).toHaveStyle({ width: '25%' })
    })

    it('shows analyzing content state', () => {
      const progressData: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content with AI...',
        progress_percent: 75,
        current_step: 'Processing financial statements',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Analyzing content with AI...')).toBeInTheDocument()
      expect(screen.getByText('Processing financial statements')).toBeInTheDocument()

      // Check for progress bar
      const progressBar = document.querySelector('.bg-blue-600')
      expect(progressBar).toHaveStyle({ width: '75%' })
    })

    it('shows completed state', () => {
      const progressData: AnalysisProgress = {
        state: 'completed',
        message: 'Analysis complete!',
        progress_percent: 100,
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={false}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Analysis complete!')).toBeInTheDocument()

      // Check for completed icon (should be green)
      const completedIcon = document.querySelector('.text-green-600')
      expect(completedIcon).toBeInTheDocument()
    })

    it('shows error state', () => {
      const progressData: AnalysisProgress = {
        state: 'error',
        message: 'Analysis failed',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={false}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Analysis failed')).toBeInTheDocument()

      // Check for error icon (should be red)
      const errorIcon = document.querySelector('.text-red-600')
      expect(errorIcon).toBeInTheDocument()
    })
  })

  describe('Button States During Progress', () => {
    const mockOnAnalyze = vi.fn()

    it('shows no button during progress states (buttons only in error/no analysis screens)', () => {
      const progressData: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content with AI...',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          onAnalyze={mockOnAnalyze}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      // Progressive loading screen doesn't have buttons
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
      expect(screen.getByText('Analyzing content with AI...')).toBeInTheDocument()
    })

    it('shows button in error state when no analysis progress', () => {
      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={{ message: 'Test error' }}
          onAnalyze={mockOnAnalyze}
          isAnalyzing={false}
          // No analysisProgress - should show error screen with button
        />
      )

      const button = screen.getByRole('button')
      expect(button).not.toBeDisabled()
      expect(button).toHaveTextContent('Retry Analysis')
    })

    it('shows button in no analysis state when no progress', () => {
      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          onAnalyze={mockOnAnalyze}
          isAnalyzing={false}
          // No analysisProgress - should show "no analysis" screen with button
        />
      )

      const button = screen.getByRole('button')
      expect(button).not.toBeDisabled()
      expect(button).toHaveTextContent('Start Analysis')
    })

    it('disables button during analysis with no progress state', () => {
      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={{ message: 'Test error' }}
          onAnalyze={mockOnAnalyze}
          isAnalyzing={true}
          // No analysisProgress - should show error screen with disabled button
        />
      )

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveTextContent('Analyzing...')
    })
  })

  describe('Backwards Compatibility', () => {
    it('falls back to simple loading when no progress data provided', () => {
      render(<FilingAnalysisSection analysis={null} isLoading={true} error={null} />)

      expect(screen.getByText('Analysis Results')).toBeInTheDocument()

      // Should show skeleton loading animation
      const skeletonElements = document.querySelectorAll('.animate-pulse')
      expect(skeletonElements.length).toBeGreaterThan(0)
    })

    it('shows completed analysis when analysis data is available', () => {
      render(<FilingAnalysisSection analysis={mockAnalysis} isLoading={false} error={null} />)

      expect(screen.getByText('Executive Summary')).toBeInTheDocument()
      expect(screen.getByText('Test executive summary')).toBeInTheDocument()
      expect(screen.getByText('Analysis Available')).toBeInTheDocument()
    })
  })

  describe('Progress Bar Functionality', () => {
    it('only shows progress bar when progress_percent is provided', () => {
      const progressWithoutPercent: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content...',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressWithoutPercent}
        />
      )

      expect(screen.getByText('Analyzing content...')).toBeInTheDocument()

      // Should not show progress bar
      const progressBar = document.querySelector('.bg-blue-600')
      expect(progressBar).toBeNull()
    })

    it('shows progress bar with correct width when progress_percent is provided', () => {
      const progressWithPercent: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content...',
        progress_percent: 60,
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressWithPercent}
        />
      )

      const progressBar = document.querySelector('.bg-blue-600')
      expect(progressBar).toBeInTheDocument()
      expect(progressBar).toHaveStyle({ width: '60%' })
    })
  })

  describe('Current Step Display', () => {
    it('shows current step when different from main message', () => {
      const progressData: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content with AI...',
        current_step: 'Processing risk factors section',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      expect(screen.getByText('Analyzing content with AI...')).toBeInTheDocument()
      expect(screen.getByText('Processing risk factors section')).toBeInTheDocument()
    })

    it('does not show duplicate current step when same as message', () => {
      const progressData: AnalysisProgress = {
        state: 'analyzing_content',
        message: 'Analyzing content with AI...',
        current_step: 'Analyzing content with AI...',
      }

      render(
        <FilingAnalysisSection
          analysis={null}
          isLoading={false}
          error={null}
          isAnalyzing={true}
          analysisProgress={progressData}
        />
      )

      const messages = screen.getAllByText('Analyzing content with AI...')
      expect(messages).toHaveLength(1) // Should only appear once
    })
  })
})
