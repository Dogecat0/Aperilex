import { useMemo, useState } from 'react'
import { ComprehensionCheckCard } from './ComprehensionCheckCard'
import { HighlightCallout } from './HighlightCallout'
import { SectionDiffDrawer } from './SectionDiffDrawer'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'
import type { ComprehensionCheck, WalkthroughPreviousComparison } from '@/lib/types/analysis'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'

interface GuidedSectionPanelProps {
  section: GuidedWalkthroughSection
  completedChecks: Record<string, true>
  onCheckCompleted(checkId: string): void
  onAnswer?(check: ComprehensionCheck, answer: string, isCorrect: boolean): void
  diff?: WalkthroughPreviousComparison | null
}

export function GuidedSectionPanel({
  section,
  completedChecks,
  onCheckCompleted,
  onAnswer,
  diff = null,
}: GuidedSectionPanelProps) {
  const [diffOpen, setDiffOpen] = useState(false)
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const diffCalloutStyles = useMemo(() => {
    const background = hexToRgba(tokens.learning.surface, isLightMode ? 0.16 : 0.24)
    return {
      background,
      borderLeftColor: tokens.learning.surface,
      backdropFilter: 'blur(8px)',
    }
  }, [isLightMode, tokens.learning.surface])

  return (
    <>
      <div
        className="flex flex-col gap-8 rounded-3xl border p-8 backdrop-blur-md"
        style={{
          background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
          borderColor: tokens.lines.subtle,
          boxShadow: tokens.shadows.soft,
        }}
      >
        <header>
          <p
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}
          >
            {section.learning_module_key}
          </p>
          <h2 className="mt-2 text-3xl font-bold text-[var(--text-primary)]">{section.title}</h2>
          <dl className="mt-6 grid gap-6 sm:grid-cols-2 pt-6 border-t border-[var(--lines-subtle)]">
            <div>
              <dt
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}
              >
                Focus
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                {section.guidance.focus}
              </dd>
            </div>
            <div>
              <dt
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}
              >
                Why it matters
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                {section.guidance.why_it_matters}
              </dd>
            </div>
          </dl>
        </header>

        {diff ? (
          <aside
            className="flex flex-col gap-3 rounded-2xl border-l-4 p-6 text-sm transition-all hover:bg-[var(--surfaces-muted)]"
            style={diffCalloutStyles}
          >
            <div className="flex flex-col gap-2">
              <p
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: tokens.learning.accent }}
              >
                Prior filing insight
              </p>
              {diff.pro_tip ? (
                <p className="font-medium" style={{ color: tokens.learning.accent }}>
                  Pro tip: {diff.pro_tip}
                </p>
              ) : null}
              <p className="text-sm" style={{ color: tokens.learning.accent }}>
                We detected updates since the last filing. Review the changes or revisit the linked
                lesson to reinforce the concept.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                type="button"
                className="rounded-full px-5 py-2 text-xs font-bold uppercase tracking-wide text-[var(--text-on-muted)] transition-transform hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
                style={{
                  background: tokens.learning.accent,
                  color: tokens.text.onBrand,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                }}
                onClick={() => setDiffOpen(true)}
              >
                View changes
              </button>
            </div>
          </aside>
        ) : null}

        <section aria-labelledby={`highlights-${section.id}`} className="flex flex-col gap-5">
          <div>
            <p
              id={`highlights-${section.id}`}
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}
            >
              Highlights
            </p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Review these callouts before attempting the comprehension checks.
            </p>
          </div>
          {section.highlights.length === 0 ? (
            <p
              className="rounded-2xl border border-dashed p-6 text-sm text-center"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
                color: 'var(--text-secondary)',
              }}
            >
              No highlights available for this section yet.
            </p>
          ) : (
            <div className="grid gap-4">
              {section.highlights.map((highlight) => (
                <HighlightCallout key={highlight.id} highlight={highlight} />
              ))}
            </div>
          )}
        </section>

        <section
          aria-labelledby={`checks-${section.id}`}
          className="flex flex-col gap-5 border-t border-[var(--lines-subtle)] pt-8"
        >
          <p
            id={`checks-${section.id}`}
            className="text-sm font-bold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}
          >
            Comprehension
          </p>
          {section.comprehension_checks.length === 0 ? (
            <p
              className="rounded-2xl border border-dashed p-6 text-sm text-center"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
                color: 'var(--text-secondary)',
              }}
            >
              No comprehension checks for this section. Continue to the next step when ready.
            </p>
          ) : (
            <div className="grid gap-4">
              {section.comprehension_checks.map((check) => (
                <ComprehensionCheckCard
                  key={check.id}
                  check={check}
                  completed={Boolean(completedChecks[check.id])}
                  onCompleted={() => onCheckCompleted(check.id)}
                  onAttempt={(answer, isCorrect) => onAnswer?.(check, answer, isCorrect)}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {diff ? (
        <SectionDiffDrawer
          isOpen={diffOpen}
          sectionTitle={section.title}
          diff={diff}
          onClose={() => setDiffOpen(false)}
        />
      ) : null}
    </>
  )
}
