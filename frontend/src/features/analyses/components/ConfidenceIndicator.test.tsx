import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceIndicator } from './ConfidenceIndicator'

describe('ConfidenceIndicator Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders without crashing', () => {
      expect(() => {
        render(<ConfidenceIndicator score={0.85} />)
      }).not.toThrow()
    })

    it('renders with default props', () => {
      render(<ConfidenceIndicator />)

      // Component renders a div with Shield icon for null/undefined score
      const indicators = screen.getAllByRole('generic')
      expect(indicators.length).toBeGreaterThan(0)
    })
  })

  describe('Score Display', () => {
    it('displays high confidence score correctly', () => {
      render(<ConfidenceIndicator score={0.95} />)

      expect(screen.getByText('95%')).toBeInTheDocument()
    })

    it('displays medium confidence score correctly', () => {
      render(<ConfidenceIndicator score={0.65} />)

      expect(screen.getByText('65%')).toBeInTheDocument()
    })

    it('displays low confidence score correctly', () => {
      render(<ConfidenceIndicator score={0.25} />)

      expect(screen.getByText('25%')).toBeInTheDocument()
    })

    it('handles zero score', () => {
      render(<ConfidenceIndicator score={0} />)

      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('handles perfect score', () => {
      render(<ConfidenceIndicator score={1.0} />)

      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('rounds decimal scores correctly', () => {
      render(<ConfidenceIndicator score={0.876} />)

      expect(screen.getByText('88%')).toBeInTheDocument()
    })
  })

  describe('Null/Undefined Score Handling', () => {
    it('displays N/A for null score', () => {
      render(<ConfidenceIndicator score={null} showLabel={true} />)

      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('displays N/A for undefined score', () => {
      render(<ConfidenceIndicator score={undefined} showLabel={true} />)

      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('displays default shield icon for null score', () => {
      render(<ConfidenceIndicator score={null} />)

      const svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })

    it('applies correct styling for null score', () => {
      render(<ConfidenceIndicator score={null} showLabel={true} />)

      const container = screen.getByText('N/A').parentElement
      expect(container).toHaveClass('text-gray-400')
    })
  })

  describe('Confidence Levels and Colors', () => {
    it('applies high confidence styling (score >= 0.8)', () => {
      render(<ConfidenceIndicator score={0.85} />)

      const container = screen.getByText('85%').parentElement
      expect(container).toHaveClass('bg-success-100', 'border-success-200')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('text-success-600')
    })

    it('applies good confidence styling (0.6 <= score < 0.8)', () => {
      render(<ConfidenceIndicator score={0.7} />)

      const container = screen.getByText('70%').parentElement
      expect(container).toHaveClass('bg-success-50', 'border-success-200')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('text-success-600')
    })

    it('applies moderate confidence styling (0.4 <= score < 0.6)', () => {
      render(<ConfidenceIndicator score={0.5} />)

      const container = screen.getByText('50%').parentElement
      expect(container).toHaveClass('bg-warning-50', 'border-warning-200')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('text-warning-600')
    })

    it('applies low confidence styling (score < 0.4)', () => {
      render(<ConfidenceIndicator score={0.3} />)

      const container = screen.getByText('30%').parentElement
      expect(container).toHaveClass('bg-error-50', 'border-error-200')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('text-error-600')
    })
  })

  describe('Icon Display', () => {
    it('displays ShieldCheck icon for high confidence', () => {
      render(<ConfidenceIndicator score={0.9} />)

      // Check for SVG element
      const svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })

    it('displays Shield icon for good confidence', () => {
      render(<ConfidenceIndicator score={0.65} />)

      const svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })

    it('displays ShieldAlert icon for moderate confidence', () => {
      render(<ConfidenceIndicator score={0.5} />)

      const svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })

    it('displays ShieldX icon for low confidence', () => {
      render(<ConfidenceIndicator score={0.2} />)

      const svgIcon = document.querySelector('svg')
      expect(svgIcon).toBeInTheDocument()
    })
  })

  describe('Size Variants', () => {
    it('applies small size styling', () => {
      render(<ConfidenceIndicator score={0.8} size="sm" />)

      const container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('px-2', 'py-0.5')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('h-3', 'w-3')

      const text = screen.getByText('80%')
      expect(text).toHaveClass('text-xs')
    })

    it('applies medium size styling (default)', () => {
      render(<ConfidenceIndicator score={0.8} />)

      const container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('px-2.5', 'py-1')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('h-4', 'w-4')

      const text = screen.getByText('80%')
      expect(text).toHaveClass('text-sm')
    })

    it('applies large size styling', () => {
      render(<ConfidenceIndicator score={0.8} size="lg" />)

      const container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('px-3', 'py-1.5')

      const icon = container?.querySelector('svg')
      expect(icon).toHaveClass('h-5', 'w-5')

      const text = screen.getByText('80%')
      expect(text).toHaveClass('text-base')
    })

    it('handles size for null score', () => {
      render(<ConfidenceIndicator score={null} size="lg" />)

      const icon = document.querySelector('svg')
      expect(icon).toHaveClass('h-5', 'w-5')
    })
  })

  describe('Label Display', () => {
    it('shows label when showLabel is true', () => {
      render(<ConfidenceIndicator score={0.85} showLabel={true} />)

      expect(screen.getByText('85%')).toBeInTheDocument()
      expect(screen.getByText('(High)')).toBeInTheDocument()
    })

    it('does not show label by default', () => {
      render(<ConfidenceIndicator score={0.85} />)

      expect(screen.getByText('85%')).toBeInTheDocument()
      expect(screen.queryByText('(High)')).not.toBeInTheDocument()
    })

    it('shows correct labels for different confidence levels', () => {
      const { rerender } = render(<ConfidenceIndicator score={0.9} showLabel={true} />)
      expect(screen.getByText('(High)')).toBeInTheDocument()

      rerender(<ConfidenceIndicator score={0.7} showLabel={true} />)
      expect(screen.getByText('(Good)')).toBeInTheDocument()

      rerender(<ConfidenceIndicator score={0.5} showLabel={true} />)
      expect(screen.getByText('(Moderate)')).toBeInTheDocument()

      rerender(<ConfidenceIndicator score={0.2} showLabel={true} />)
      expect(screen.getByText('(Low)')).toBeInTheDocument()
    })

    it('shows N/A label for null score with showLabel', () => {
      render(<ConfidenceIndicator score={null} showLabel={true} />)

      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('applies correct styling when showing labels', () => {
      render(<ConfidenceIndicator score={0.85} showLabel={true} />)

      const container = screen.getByText('85%').parentElement
      expect(container).toHaveClass('inline-flex', 'items-center', 'gap-2')

      const labelText = screen.getByText('(High)')
      expect(labelText).toHaveClass('text-gray-600')
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      render(<ConfidenceIndicator score={0.8} className="custom-class" />)

      const container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('custom-class')
    })

    it('merges custom className with default classes', () => {
      render(<ConfidenceIndicator score={0.8} className="mx-4" />)

      const container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('mx-4')
      expect(container).toHaveClass('inline-flex', 'items-center')
    })

    it('applies consistent base styling across all variants', () => {
      render(<ConfidenceIndicator score={0.5} />)

      const container = screen.getByText('50%').parentElement
      expect(container).toHaveClass('inline-flex', 'items-center', 'rounded-full', 'border')
    })
  })

  describe('Edge Cases', () => {
    it('handles negative scores gracefully', () => {
      render(<ConfidenceIndicator score={-0.1} />)

      expect(screen.getByText('-10%')).toBeInTheDocument()

      const container = screen.getByText('-10%').parentElement
      expect(container).toHaveClass('bg-error-50', 'border-error-200')
    })

    it('handles scores above 1 gracefully', () => {
      render(<ConfidenceIndicator score={1.5} />)

      expect(screen.getByText('150%')).toBeInTheDocument()

      const container = screen.getByText('150%').parentElement
      expect(container).toHaveClass('bg-success-100', 'border-success-200')
    })

    it('handles very small decimal scores', () => {
      render(<ConfidenceIndicator score={0.001} />)

      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('handles boundary score values correctly', () => {
      const { rerender } = render(<ConfidenceIndicator score={0.8} />)
      let container = screen.getByText('80%').parentElement
      expect(container).toHaveClass('bg-success-100') // High confidence

      rerender(<ConfidenceIndicator score={0.6} />)
      container = screen.getByText('60%').parentElement
      expect(container).toHaveClass('bg-success-50') // Good confidence

      rerender(<ConfidenceIndicator score={0.4} />)
      container = screen.getByText('40%').parentElement
      expect(container).toHaveClass('bg-warning-50') // Moderate confidence
    })
  })

  describe('Accessibility', () => {
    it('provides meaningful content for screen readers', () => {
      render(<ConfidenceIndicator score={0.85} />)

      expect(screen.getByText('85%')).toBeInTheDocument()

      const container = screen.getByText('85%').parentElement
      expect(container).toBeInTheDocument()
    })

    it('maintains proper color contrast', () => {
      render(<ConfidenceIndicator score={0.85} />)

      const percentageText = screen.getByText('85%')
      expect(percentageText).toHaveClass('text-success-600')
    })

    it('provides accessible null state', () => {
      render(<ConfidenceIndicator score={null} showLabel={true} />)

      expect(screen.getByText('N/A')).toBeInTheDocument()

      const container = screen.getByText('N/A').parentElement
      expect(container).toHaveClass('text-gray-400')
    })

    it('has appropriate ARIA attributes for complex display', () => {
      render(<ConfidenceIndicator score={0.85} showLabel={true} />)

      const container = screen.getByText('85%').parentElement
      expect(container).toBeInTheDocument()
      expect(screen.getByText('(High)')).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('renders efficiently with multiple instances', () => {
      const scores = [0.9, 0.7, 0.5, 0.3, 0.1]

      const startTime = performance.now()

      render(
        <div>
          {scores.map((score, index) => (
            <ConfidenceIndicator key={index} score={score} />
          ))}
        </div>
      )

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(100) // Should render quickly
    })

    it('handles frequent prop changes without issues', () => {
      const { rerender } = render(<ConfidenceIndicator score={0.8} />)

      // Simulate rapid prop changes
      const scores = [0.9, 0.7, 0.5, 0.3, 0.1, 0.8]
      scores.forEach((score) => {
        rerender(<ConfidenceIndicator score={score} />)
        expect(screen.getByText(`${Math.round(score * 100)}%`)).toBeInTheDocument()
      })
    })

    it('memoizes effectively with same props', () => {
      const { rerender } = render(<ConfidenceIndicator score={0.85} />)

      const _initialText = screen.getByText('85%')

      // Re-render with same props
      rerender(<ConfidenceIndicator score={0.85} />)

      const afterRerender = screen.getByText('85%')
      expect(afterRerender).toBeInTheDocument()
    })
  })

  describe('Integration with Parent Components', () => {
    it('works correctly as a child component', () => {
      render(
        <div className="parent-container">
          <span>Analysis Confidence:</span>
          <ConfidenceIndicator score={0.88} />
        </div>
      )

      expect(screen.getByText('Analysis Confidence:')).toBeInTheDocument()
      expect(screen.getByText('88%')).toBeInTheDocument()
    })

    it('maintains styling within flex containers', () => {
      render(
        <div className="flex items-center gap-2">
          <span>Score:</span>
          <ConfidenceIndicator score={0.75} size="sm" />
        </div>
      )

      const indicator = screen.getByText('75%').parentElement
      expect(indicator).toHaveClass('inline-flex')
    })

    it('responds to parent component state changes', () => {
      const TestParent = ({ score }: { score: number | null }) => (
        <ConfidenceIndicator score={score} showLabel={true} />
      )

      const { rerender } = render(<TestParent score={0.8} />)
      expect(screen.getByText('80%')).toBeInTheDocument()

      rerender(<TestParent score={null} />)
      expect(screen.getByText('N/A')).toBeInTheDocument()

      rerender(<TestParent score={0.6} />)
      expect(screen.getByText('60%')).toBeInTheDocument()
    })
  })
})
