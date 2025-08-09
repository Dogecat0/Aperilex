import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RiskFactorCard, RiskFactorList } from './RiskFactorCard'
import type { RiskFactor } from '@/api/types'

// Mock Button component
vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, className }: any) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
}))

const mockRiskObject: RiskFactor = {
  risk_name: 'Market Volatility Risk',
  category: 'Market',
  description:
    'The company faces significant exposure to market volatility which could impact financial performance and operational stability.',
  severity: 'High',
  probability: 'Moderate',
  potential_impact: 'Significant revenue fluctuations and operational disruptions',
  mitigation_measures: [
    'Diversify product portfolio',
    'Implement hedging strategies',
    'Maintain strong cash reserves',
  ],
  timeline: 'Ongoing risk with potential immediate impact',
}

const mockRiskString = 'Simple risk factor description as a string'

describe('RiskFactorCard', () => {
  describe('with object risk data', () => {
    it('renders risk card with all elements', () => {
      render(<RiskFactorCard risk={mockRiskObject} />)

      expect(screen.getByText('Market Volatility Risk')).toBeInTheDocument()
      expect(screen.getByText('High')).toBeInTheDocument()
      expect(screen.getByText('Market')).toBeInTheDocument()
      expect(screen.getByText('Moderate')).toBeInTheDocument()
      expect(screen.getByText(mockRiskObject.description)).toBeInTheDocument()
    })

    it('shows expand button when additional details are available', () => {
      render(<RiskFactorCard risk={mockRiskObject} />)

      const expandButton = screen.getByLabelText('Expand details')
      expect(expandButton).toBeInTheDocument()
    })

    it('expands to show detailed information when clicked', () => {
      render(<RiskFactorCard risk={mockRiskObject} />)

      const expandButton = screen.getByLabelText('Expand details')
      fireEvent.click(expandButton)

      expect(screen.getByText('Potential Impact')).toBeInTheDocument()
      expect(screen.getByText('Timeline')).toBeInTheDocument()
      expect(screen.getByText('Mitigation Measures')).toBeInTheDocument()
      expect(screen.getByText('Diversify product portfolio')).toBeInTheDocument()
      expect(screen.getByLabelText('Collapse details')).toBeInTheDocument()
    })

    it('applies correct severity styling', () => {
      const { rerender } = render(<RiskFactorCard risk={mockRiskObject} />)

      // High severity should have orange styling
      expect(screen.getByText('High')).toHaveClass('text-orange-800')

      const criticalRisk: RiskFactor = { ...mockRiskObject, severity: 'Critical' }
      rerender(<RiskFactorCard risk={criticalRisk} />)

      // Critical severity should have red styling
      expect(screen.getByText('Critical')).toHaveClass('text-red-800')
    })
  })

  describe('with string risk data', () => {
    it('renders simple string risk', () => {
      render(<RiskFactorCard risk={mockRiskString} index={1} />)

      expect(screen.getByText('Risk Factor 2')).toBeInTheDocument()
      expect(screen.getByText('Medium')).toBeInTheDocument() // default severity
      expect(screen.getByText(mockRiskString)).toBeInTheDocument()
    })

    it('shows read more button for long text', () => {
      const longText = 'a'.repeat(250)
      render(<RiskFactorCard risk={longText} />)

      expect(screen.getByText('Read more')).toBeInTheDocument()

      fireEvent.click(screen.getByText('Read more'))
      expect(screen.getByText(longText)).toBeInTheDocument()
    })
  })

  describe('with action buttons', () => {
    it('renders action buttons when provided', () => {
      const onViewDetails = vi.fn()
      const onAddToWatchlist = vi.fn()

      render(
        <RiskFactorCard
          risk={mockRiskObject}
          onViewDetails={onViewDetails}
          onAddToWatchlist={onAddToWatchlist}
        />
      )

      expect(screen.getByText('View Details')).toBeInTheDocument()
      expect(screen.getByText('Monitor Risk')).toBeInTheDocument()
    })

    it('calls action handlers when buttons are clicked', () => {
      const onViewDetails = vi.fn()
      const onAddToWatchlist = vi.fn()

      render(
        <RiskFactorCard
          risk={mockRiskObject}
          onViewDetails={onViewDetails}
          onAddToWatchlist={onAddToWatchlist}
        />
      )

      fireEvent.click(screen.getByText('View Details'))
      expect(onViewDetails).toHaveBeenCalledTimes(1)

      fireEvent.click(screen.getByText('Monitor Risk'))
      expect(onAddToWatchlist).toHaveBeenCalledTimes(1)
    })
  })
})

describe('RiskFactorList', () => {
  const mockRisks = [mockRiskObject, mockRiskString]

  it('renders list of risks', () => {
    render(<RiskFactorList risks={mockRisks} />)

    expect(screen.getByText('Risk Factors')).toBeInTheDocument()
    expect(screen.getByText('2 risks identified')).toBeInTheDocument()
    expect(screen.getByText('Market Volatility Risk')).toBeInTheDocument()
    expect(screen.getByText('Risk Factor 2')).toBeInTheDocument()
  })

  it('renders custom title', () => {
    render(<RiskFactorList risks={mockRisks} title="Custom Risk Title" />)

    expect(screen.getByText('Custom Risk Title')).toBeInTheDocument()
  })

  it('hides header when requested', () => {
    render(<RiskFactorList risks={mockRisks} showHeader={false} />)

    expect(screen.queryByText('Risk Factors')).not.toBeInTheDocument()
    expect(screen.getByText('Market Volatility Risk')).toBeInTheDocument()
  })

  it('shows empty state when no risks provided', () => {
    render(<RiskFactorList risks={[]} />)

    expect(screen.getByText('No risk factors identified')).toBeInTheDocument()
  })

  it('calls risk action handlers with correct index', () => {
    const onViewRiskDetails = vi.fn()
    const onAddRiskToWatchlist = vi.fn()

    render(
      <RiskFactorList
        risks={mockRisks}
        onViewRiskDetails={onViewRiskDetails}
        onAddRiskToWatchlist={onAddRiskToWatchlist}
      />
    )

    const viewButtons = screen.getAllByText('View Details')
    const monitorButtons = screen.getAllByText('Monitor Risk')

    fireEvent.click(viewButtons[0])
    expect(onViewRiskDetails).toHaveBeenCalledWith(0)

    fireEvent.click(monitorButtons[1])
    expect(onAddRiskToWatchlist).toHaveBeenCalledWith(1)
  })
})
