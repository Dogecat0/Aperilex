import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderWithProviders } from '@/test/utils'
import type { HeadlineMetric } from '@/lib/types/analysis'
import { NumbersTab } from './NumbersTab'

describe('NumbersTab', () => {
  it('renders metrics without delta text copy', () => {
    const deltaText = 'Revenue climbed $6.1B versus prior-year quarter on services momentum.'
    const metrics: HeadlineMetric[] = [
      {
        id: 'total_revenue',
        name: 'Total Revenue',
        category: 'growth',
        display: {
          current: '$118.4B',
          delta: '+$6.1B',
          delta_text: deltaText,
        },
      },
    ]

    renderWithProviders(<NumbersTab metrics={metrics} />)

    expect(screen.getByText('Total Revenue')).toBeInTheDocument()
    expect(screen.getByText('$118.4B')).toBeInTheDocument()
    expect(screen.getByText('+$6.1B')).toBeInTheDocument()
    expect(screen.queryByText(deltaText)).not.toBeInTheDocument()
  })
})
