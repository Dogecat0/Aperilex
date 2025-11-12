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
  activeAnalyses: 2,
  nextLesson: {
    moduleKey: 'mda_foundations',
    sectionKey: 'item-7',
    title: 'Decode MD&A narratives',
    summary: 'Connect commentary back to margin changes from your latest filing.',
    duration: '9 min walkthrough',
    progressPercent: 60,
    isUnlocked: true,
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
    expect(screen.getByText('Module coverage')).toBeInTheDocument()
    expect(screen.getByText('3/4')).toBeInTheDocument()
    expect(
      screen.getByText(/Completed 1 · In progress 2 · Not started 1 · Active analyses 2/i)
    ).toBeInTheDocument()
    expect(screen.getByText('Sections complete')).toBeInTheDocument()
    expect(screen.getByText('2/5')).toBeInTheDocument()
    expect(screen.getByText(/Active 4 · In progress 2 · Queued 1/i)).toBeInTheDocument()
    expect(screen.getByText('Next lesson')).toBeInTheDocument()
    expect(screen.getByText('Decode MD&A narratives')).toBeInTheDocument()
    expect(
      screen.getByText(
        /Connect commentary back to margin changes from your latest filing\. · 9 min walkthrough · 60% complete/i
      )
    ).toBeInTheDocument()
  })
})
