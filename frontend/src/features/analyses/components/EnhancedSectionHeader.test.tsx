import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Download, Share, Settings } from 'lucide-react'
import { EnhancedSectionHeader, getAnalysisType, extractSectionMetadata } from './EnhancedSectionHeader'

describe('EnhancedSectionHeader', () => {
  it('renders basic header with title', () => {
    render(<EnhancedSectionHeader title="Test Section" />)
    expect(screen.getByText('Test Section')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(
      <EnhancedSectionHeader title="Test Section" subtitle="This is a test subtitle" />
    )
    expect(screen.getByText('This is a test subtitle')).toBeInTheDocument()
  })

  it('applies different gradient themes for each analysis type', () => {
    const { container, rerender } = render(
      <EnhancedSectionHeader title="Financial" analysisType="financial" />
    )
    // Check for the gradient classes in the header container
    const headerContainer = container.querySelector('[class*="bg-gradient-to-r"]')
    expect(headerContainer).toHaveClass('bg-gradient-to-r', 'from-blue-500')

    rerender(<EnhancedSectionHeader title="Risk" analysisType="risk" />)
    const riskHeaderContainer = container.querySelector('[class*="bg-gradient-to-r"]')
    expect(riskHeaderContainer).toHaveClass('bg-gradient-to-r', 'from-red-500')

    rerender(<EnhancedSectionHeader title="Business" analysisType="business" />)
    const businessHeaderContainer = container.querySelector('[class*="bg-gradient-to-r"]')
    expect(businessHeaderContainer).toHaveClass('bg-gradient-to-r', 'from-teal-500')

    rerender(<EnhancedSectionHeader title="Default" analysisType="default" />)
    const defaultHeaderContainer = container.querySelector('[class*="bg-gradient-to-r"]')
    expect(defaultHeaderContainer).toHaveClass('bg-gradient-to-r', 'from-gray-500')
  })

  it('renders different sizes correctly', () => {
    const { rerender } = render(
      <EnhancedSectionHeader title="Small" size="sm" />
    )
    expect(screen.getByText('Small')).toHaveClass('text-sm', 'font-semibold')

    rerender(<EnhancedSectionHeader title="Medium" size="md" />)
    expect(screen.getByText('Medium')).toHaveClass('text-lg', 'font-semibold')

    rerender(<EnhancedSectionHeader title="Large" size="lg" />)
    expect(screen.getByText('Large')).toHaveClass('text-xl', 'font-bold')
  })

  it('renders metadata information correctly', () => {
    const metadata = {
      confidence: 0.85,
      processingTimeMs: 2500,
      subSectionCount: 5,
      totalItems: 15
    }

    render(
      <EnhancedSectionHeader
        title="Test"
        metadata={metadata}
      />
    )

    expect(screen.getByText('3s')).toBeInTheDocument() // Processing time
    expect(screen.getByText('5 sections')).toBeInTheDocument()
    expect(screen.getByText('15 items')).toBeInTheDocument()
  })

  it('renders confidence indicator when confidence is provided', () => {
    const metadata = { confidence: 0.75 }

    render(
      <EnhancedSectionHeader
        title="Test"
        metadata={metadata}
      />
    )

    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('handles expand/collapse toggle', () => {
    const mockToggle = vi.fn()

    render(
      <EnhancedSectionHeader
        title="Test"
        isExpanded={false}
        onToggle={mockToggle}
      />
    )

    const toggleButton = screen.getByTitle('Expand section')
    fireEvent.click(toggleButton)

    expect(mockToggle).toHaveBeenCalledTimes(1)
  })

  it('shows different chevron icons based on expanded state', () => {
    const { rerender } = render(
      <EnhancedSectionHeader
        title="Test"
        isExpanded={false}
        onToggle={() => {}}
      />
    )

    expect(screen.getByTitle('Expand section')).toBeInTheDocument()

    rerender(
      <EnhancedSectionHeader
        title="Test"
        isExpanded={true}
        onToggle={() => {}}
      />
    )

    expect(screen.getByTitle('Collapse section')).toBeInTheDocument()
  })

  it('renders default quick actions (export and share)', () => {
    const mockExport = vi.fn()
    const mockShare = vi.fn()

    render(
      <EnhancedSectionHeader
        title="Test"
        quickActions={{
          showExport: true,
          showShare: true,
          onExport: mockExport,
          onShare: mockShare,
        }}
      />
    )

    const exportButton = screen.getByTitle('Export')
    const shareButton = screen.getByTitle('Share')

    fireEvent.click(exportButton)
    fireEvent.click(shareButton)

    expect(mockExport).toHaveBeenCalledTimes(1)
    expect(mockShare).toHaveBeenCalledTimes(1)
  })

  it('renders custom quick actions', () => {
    const mockCustomAction = vi.fn()
    const customActions = [
      {
        icon: Settings,
        label: 'Settings',
        onClick: mockCustomAction,
      }
    ]

    render(
      <EnhancedSectionHeader
        title="Test"
        quickActions={{ customActions }}
      />
    )

    const settingsButton = screen.getByTitle('Settings')
    fireEvent.click(settingsButton)

    expect(mockCustomAction).toHaveBeenCalledTimes(1)
  })

  it('disables quick actions when disabled prop is true', () => {
    const mockDisabledAction = vi.fn()
    const customActions = [
      {
        icon: Settings,
        label: 'Disabled Action',
        onClick: mockDisabledAction,
        disabled: true,
      }
    ]

    render(
      <EnhancedSectionHeader
        title="Test"
        quickActions={{ customActions }}
      />
    )

    const disabledButton = screen.getByTitle('Disabled Action')
    expect(disabledButton).toBeDisabled()

    fireEvent.click(disabledButton)
    expect(mockDisabledAction).not.toHaveBeenCalled()
  })

  it('shows additional info bar when metadata has sub-sections or total items', () => {
    const metadata = {
      subSectionCount: 3,
      totalItems: 10,
      confidence: 0.9
    }

    render(
      <EnhancedSectionHeader
        title="Test"
        metadata={metadata}
        analysisType="financial"
      />
    )

    expect(screen.getByText('3 sub-sections analyzed')).toBeInTheDocument()
    expect(screen.getByText('10 data points extracted')).toBeInTheDocument()
    expect(screen.getByText('Analysis confidence: 90%')).toBeInTheDocument()
  })

  it('applies hover effects correctly', async () => {
    const { container } = render(<EnhancedSectionHeader title="Test" analysisType="financial" />)

    const headerElement = container.querySelector('[data-testid]') || container.firstChild as HTMLElement

    fireEvent.mouseEnter(headerElement)

    await waitFor(() => {
      expect(headerElement).toHaveClass('shadow-md')
    })

    fireEvent.mouseLeave(headerElement)

    await waitFor(() => {
      expect(headerElement).toHaveClass('shadow-sm')
    })
  })

  it('applies custom className', () => {
    const { container } = render(
      <EnhancedSectionHeader title="Test" className="custom-class" />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('formats processing time correctly', () => {
    const { rerender } = render(
      <EnhancedSectionHeader
        title="Test"
        metadata={{ processingTimeMs: 500 }}
      />
    )
    expect(screen.getByText('500ms')).toBeInTheDocument()

    rerender(
      <EnhancedSectionHeader
        title="Test"
        metadata={{ processingTimeMs: 2500 }}
      />
    )
    expect(screen.getByText('3s')).toBeInTheDocument()
  })
})

describe('getAnalysisType helper', () => {
  it('correctly identifies financial analysis types', () => {
    expect(getAnalysisType('Financial Statement')).toBe('financial')
    expect(getAnalysisType('Balance Sheet Analysis')).toBe('financial')
    expect(getAnalysisType('Income Statement')).toBe('financial')
    expect(getAnalysisType('Cash Flow Statement')).toBe('financial')
  })

  it('correctly identifies risk analysis types', () => {
    expect(getAnalysisType('Risk Factors')).toBe('risk')
    expect(getAnalysisType('Risk Assessment')).toBe('risk')
    expect(getAnalysisType('Factor Analysis')).toBe('risk')
  })

  it('correctly identifies business analysis types', () => {
    expect(getAnalysisType('Business Overview')).toBe('business')
    expect(getAnalysisType('Operational Analysis')).toBe('business')
    expect(getAnalysisType('Market Analysis')).toBe('business')
  })

  it('returns default for unrecognized types', () => {
    expect(getAnalysisType('Unknown Section')).toBe('default')
    expect(getAnalysisType('Random Analysis')).toBe('default')
  })
})

describe('extractSectionMetadata helper', () => {
  it('extracts metadata from section object correctly', () => {
    const section = {
      confidence_score: 0.85,
      processing_time_ms: 2500,
      sub_section_count: 5,
      total_items: 15
    }

    const metadata = extractSectionMetadata(section)

    expect(metadata).toEqual({
      confidence: 0.85,
      processingTimeMs: 2500,
      subSectionCount: 5,
      totalItems: 15
    })
  })

  it('handles alternative field names', () => {
    const section = {
      overall_confidence: 0.75,
      sub_sections: [{}, {}, {}] // Length should be used
    }

    const metadata = extractSectionMetadata(section)

    expect(metadata).toEqual({
      confidence: 0.75,
      processingTimeMs: null,
      subSectionCount: 3,
      totalItems: null
    })
  })

  it('handles missing fields gracefully', () => {
    const section = {}

    const metadata = extractSectionMetadata(section)

    expect(metadata).toEqual({
      confidence: null,
      processingTimeMs: null,
      subSectionCount: 0,
      totalItems: null
    })
  })
})
