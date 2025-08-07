import { render, screen, fireEvent } from '@testing-library/react'
import { FinancialMetricsGrid } from './FinancialMetricsGrid'
import type { FinancialMetric } from './FinancialMetricsGrid'

const mockMetrics: FinancialMetric[] = [
  {
    metric_name: 'Total Revenue',
    current_value: '50000000000',
    previous_value: '45000000000',
    percentage_change: '+11.1%',
    direction: 'Increased',
    explanation: 'Revenue increased due to strong product sales and market expansion',
    significance: 'This represents significant growth in the company\'s core business',
  },
  {
    metric_name: 'Net Profit Margin',
    current_value: '15.2%',
    previous_value: '12.8%',
    percentage_change: '+2.4%',
    direction: 'Increased',
    explanation: 'Improved operational efficiency and cost management',
  },
  {
    ratio_name: 'Debt-to-Equity Ratio',
    current_value: 0.45,
    previous_value: 0.52,
    industry_benchmark: 0.40,
    interpretation: 'Company has reduced debt relative to equity, approaching industry average',
  },
  {
    metric_name: 'Operating Cash Flow',
    current_value: '8500000000',
    explanation: 'Strong cash generation from operations',
  },
]

describe('FinancialMetricsGrid', () => {
  it('renders loading state correctly', () => {
    render(<FinancialMetricsGrid metrics={[]} loading={true} />)
    
    expect(screen.getByText(/Loading Financial Metrics/)).toBeInTheDocument()
    // Check for loading animation instead of label
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders empty state when no metrics provided', () => {
    render(<FinancialMetricsGrid metrics={[]} />)
    
    expect(screen.getByText('No Financial Metrics Available')).toBeInTheDocument()
    expect(screen.getByText(/Financial metrics will appear here/)).toBeInTheDocument()
  })

  it('renders metrics grid with provided data', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} />)
    
    // Check header
    expect(screen.getByText('Financial Metrics')).toBeInTheDocument()
    expect(screen.getByText('4 metrics')).toBeInTheDocument()
    
    // Check individual metrics
    expect(screen.getByText('Total Revenue')).toBeInTheDocument()
    expect(screen.getByText('$50.0B')).toBeInTheDocument()
    expect(screen.getByText('+11.1%')).toBeInTheDocument()
    
    expect(screen.getByText('Net Profit Margin')).toBeInTheDocument()
    expect(screen.getByText('15.2%')).toBeInTheDocument()
    
    expect(screen.getByText('Debt-to-Equity Ratio')).toBeInTheDocument()
    expect(screen.getByText('0.45')).toBeInTheDocument()
    
    expect(screen.getByText('Operating Cash Flow')).toBeInTheDocument()
    expect(screen.getByText('$8.5B')).toBeInTheDocument()
  })

  it('shows previous values and changes when available', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} showComparisons={true} />)
    
    expect(screen.getByText('Previous: $45.0B')).toBeInTheDocument()
    expect(screen.getByText('Previous: 12.8%')).toBeInTheDocument()
    expect(screen.getByText('Previous: 0.52')).toBeInTheDocument()
  })

  it('hides comparisons when showComparisons is false', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} showComparisons={false} />)
    
    expect(screen.queryByText('Previous: $45.0B')).not.toBeInTheDocument()
    expect(screen.queryByText('+11.1%')).not.toBeInTheDocument()
  })

  it('highlights significant metrics when highlightSignificant is true', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} highlightSignificant={true} />)
    
    // The first metric should have a "Key" badge due to its significance
    const significantMetric = screen.getByText('Total Revenue').closest('.border')
    expect(significantMetric).toHaveClass('border-blue-300')
    expect(screen.getByText('Key')).toBeInTheDocument()
  })

  it('expands metric details when More Info is clicked', async () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} />)
    
    const moreInfoButton = screen.getAllByText('More Info')[0]
    fireEvent.click(moreInfoButton)
    
    expect(screen.getByText('Explanation')).toBeInTheDocument()
    expect(screen.getByText(/Revenue increased due to strong product sales/)).toBeInTheDocument()
    
    // Button should change to "Less Info"
    expect(screen.getByText('Less Info')).toBeInTheDocument()
  })

  it('shows industry benchmarks when available', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} />)
    
    expect(screen.getByText(/Industry avg:/)).toBeInTheDocument()
    expect(screen.getByText('0.40')).toBeInTheDocument()
  })

  it('limits display count when maxDisplayCount is set', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} maxDisplayCount={2} />)
    
    expect(screen.getByText('Total Revenue')).toBeInTheDocument()
    expect(screen.getByText('Net Profit Margin')).toBeInTheDocument()
    expect(screen.queryByText('Debt-to-Equity Ratio')).not.toBeInTheDocument()
    
    // Should show "Show All" button
    expect(screen.getByText('Show All (4)')).toBeInTheDocument()
  })

  it('expands to show all metrics when Show All is clicked', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} maxDisplayCount={2} />)
    
    const showAllButton = screen.getByText('Show All (4)')
    fireEvent.click(showAllButton)
    
    expect(screen.getByText('Debt-to-Equity Ratio')).toBeInTheDocument()
    expect(screen.getByText('Operating Cash Flow')).toBeInTheDocument()
    expect(screen.getByText('Show Less')).toBeInTheDocument()
  })

  it('formats currency values correctly', () => {
    const currencyMetrics = [
      { metric_name: 'Small Revenue Amount', current_value: 1500 },
      { metric_name: 'Revenue Thousands', current_value: 25000 },
      { metric_name: 'Revenue Millions', current_value: 50000000 },
      { metric_name: 'Revenue Billions', current_value: 75000000000 },
      { metric_name: 'Revenue Trillions', current_value: 1500000000000 },
    ]
    
    render(<FinancialMetricsGrid metrics={currencyMetrics} />)
    
    expect(screen.getByText('$1.5K')).toBeInTheDocument()
    expect(screen.getByText('$25.0K')).toBeInTheDocument()
    expect(screen.getByText('$50.0M')).toBeInTheDocument()
    expect(screen.getByText('$75.0B')).toBeInTheDocument()
    expect(screen.getByText('$1.5T')).toBeInTheDocument()
  })

  it('determines metric types correctly', () => {
    const mixedMetrics = [
      { metric_name: 'Revenue Growth Rate', current_value: '15.5%' },
      { metric_name: 'P/E Ratio', current_value: 18.5 },
      { metric_name: 'Total Assets', current_value: '500000000' },
      { metric_name: 'Employee Count', current_value: 50000 },
    ]
    
    render(<FinancialMetricsGrid metrics={mixedMetrics} />)
    
    // Should show appropriate formatting
    expect(screen.getByText('15.5%')).toBeInTheDocument() // percentage preserved
    expect(screen.getByText('18.50')).toBeInTheDocument() // ratio format
    expect(screen.getByText('$500.0M')).toBeInTheDocument() // currency format
    expect(screen.getByText('50.0K')).toBeInTheDocument() // number format
  })

  it('applies custom className', () => {
    const { container } = render(
      <FinancialMetricsGrid metrics={mockMetrics} className="custom-class" />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('uses custom title', () => {
    render(<FinancialMetricsGrid metrics={mockMetrics} title="Custom Title" />)
    
    expect(screen.getByText('Custom Title')).toBeInTheDocument()
  })
})

// Test the metric type determination logic
describe('FinancialMetricsGrid - Metric Type Detection', () => {
  it('detects currency metrics correctly', () => {
    const currencyMetrics = [
      { metric_name: 'Revenue', current_value: 1000000 },
      { metric_name: 'Net Income', current_value: 500000 },
      { metric_name: 'Total Assets', current_value: 2000000 },
      { metric_name: 'Cash Flow', current_value: 300000 },
      { metric_name: 'Debt Outstanding', current_value: 800000 },
    ]
    
    render(<FinancialMetricsGrid metrics={currencyMetrics} />)
    
    // All should be formatted as currency
    expect(screen.getByText('$1.0M')).toBeInTheDocument()
    expect(screen.getByText('$500.0K')).toBeInTheDocument()
    expect(screen.getByText('$2.0M')).toBeInTheDocument()
    expect(screen.getByText('$300.0K')).toBeInTheDocument()
    expect(screen.getByText('$800.0K')).toBeInTheDocument()
  })

  it('detects percentage metrics correctly', () => {
    const percentageMetrics = [
      { metric_name: 'Gross Margin', current_value: 25.5 },
      { metric_name: 'Return Rate', current_value: 12.3 },
      { metric_name: 'Growth Percentage', current_value: 8.7 },
      { metric_name: 'Market Share', current_value: '15.2%' },
    ]
    
    render(<FinancialMetricsGrid metrics={percentageMetrics} />)
    
    // Should be formatted as percentages
    expect(screen.getByText('25.5%')).toBeInTheDocument()
    expect(screen.getByText('12.3%')).toBeInTheDocument()
    expect(screen.getByText('8.7%')).toBeInTheDocument()
    expect(screen.getByText('15.2%')).toBeInTheDocument() // Preserved existing format
  })

  it('detects ratio metrics correctly', () => {
    const ratioMetrics = [
      { ratio_name: 'P/E Ratio', current_value: 18.5 },
      { metric_name: 'Current Ratio', current_value: 2.1 },
      { metric_name: 'Debt-to-Equity Ratio', current_value: 0.45 },
      { metric_name: 'Price-to-Book Multiple', current_value: 1.8 },
    ]
    
    render(<FinancialMetricsGrid metrics={ratioMetrics} />)
    
    // Should be formatted as ratios (2 decimal places)
    expect(screen.getByText('18.50')).toBeInTheDocument()
    expect(screen.getByText('2.10')).toBeInTheDocument()
    expect(screen.getByText('0.45')).toBeInTheDocument()
    expect(screen.getByText('1.80')).toBeInTheDocument()
  })
})