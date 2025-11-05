import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { LearningDashboardHighlights } from '@/lib/hooks'
import { LearningProgressHero } from './LearningProgressHero'

const sampleHighlights: LearningDashboardHighlights = {
  completion: {
    total: 4,
    completed: 1,
    inProgress: 2,
    queued: 1,
    unlocked: 3,
    locked: 1,
  },
  sectionSummary: {
    total: 5,
    completed: 2,
    inProgress: 2,
    queued: 1,
  },
  pendingReviewTotal: 3,
  activeAnalyses: 2,
  nextLesson: {
    moduleKey: 'mda_foundations',
    sectionKey: 'item-7',
    title: 'Decode MD&A narratives',
    summary: 'Connect commentary back to margin changes from your latest filing.',
    duration: '9 min walkthrough',
    progressPercent: 60,
    isUnlocked: true,
    pendingReviewCount: 2,
  },
}

describe('LearningProgressHero', () => {
  it('renders updated progress summaries and recommendations', () => {
    render(
      <MemoryRouter>
        <LearningProgressHero highlights={sampleHighlights} isLoading={false} />
      </MemoryRouter>
    )

    expect(
      screen.getByRole('heading', { name: /learning hub momentum overview/i })
    ).toBeInTheDocument()
    expect(screen.getByText('2/5 sections complete')).toBeInTheDocument()
    expect(screen.getByText(/Pending reviews 3/i)).toBeInTheDocument()
    expect(screen.getByText(/Active analyses/i).nextElementSibling?.textContent).toBe('2')
    expect(screen.getByText(/60% complete · 2 pending review/i)).toBeInTheDocument()
  })
})
