import { useMemo } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { SectionAnalysis } from '@/lib/types/analysis'

interface RawSectionTabProps {
  sections: SectionAnalysis[]
}

export function RawSectionTab({ sections }: RawSectionTabProps) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'

  if (!sections || sections.length === 0) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm"
        style={{
          background: 'var(--surfaces-raised)',
          borderColor: 'var(--lines-subtle)',
          color: 'var(--text-secondary)',
          boxShadow: tokens.shadows.soft,
        }}
      >
        Structured section analyses are not available for this filing. Use the guided walkthrough to
        review highlights.
      </div>
    )
  }

  const cardStyles = useMemo(
    () => ({
      background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
      borderColor: tokens.lines.subtle,
      backdropFilter: 'blur(12px)',
      boxShadow: tokens.shadows.soft,
    }),
    [tokens]
  )
  const subSectionStyles = useMemo(
    () => ({
      background: 'var(--surfaces-muted)',
      borderColor: 'var(--lines-subtle)',
    }),
    []
  )

  return (
    <div className="flex flex-col gap-8">
      {sections.map((section, index) => (
        <section
          key={section.section_name || index}
          className="flex flex-col gap-6 rounded-3xl border p-8 transition-all hover:shadow-lg"
          style={cardStyles}
        >
          <header className="flex flex-col gap-2 border-b border-[var(--lines-subtle)] pb-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-[var(--text-primary)]">{section.section_name}</h2>
              <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide bg-[var(--surfaces-muted)] text-[var(--text-secondary)]">
                {section.sub_section_count ?? 0} Subsections
              </span>
            </div>
            {section.section_summary ? (
              <p className="text-base leading-relaxed text-[var(--text-secondary)]">
                {section.section_summary}
              </p>
            ) : null}
          </header>

          {section.consolidated_insights && section.consolidated_insights.length > 0 ? (
            <div className="flex flex-col gap-4">
              <h3
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}
              >
                Key Insights
              </h3>
              <ul className="grid gap-3 sm:grid-cols-2">
                {section.consolidated_insights.map((insight, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 rounded-xl p-4 text-sm text-[var(--text-secondary)]"
                    style={subSectionStyles}
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand-accent)]" />
                    <span className="leading-relaxed">{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.critical_findings && section.critical_findings.length > 0 ? (
            <div className="flex flex-col gap-4">
              <h3
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: tokens.status.warning }}
              >
                Critical Findings
              </h3>
              <ul className="flex flex-col gap-3">
                {section.critical_findings.map((finding, i) => (
                  <li
                    key={i}
                    className="flex gap-4 rounded-xl border border-l-4 p-5 text-sm"
                    style={{
                      background: hexToRgba(tokens.status.warning, isLightMode ? 0.08 : 0.16),
                      borderColor: hexToRgba(tokens.status.warning, 0.3),
                      borderLeftColor: tokens.status.warning,
                      color: tokens.text.primary,
                    }}
                  >
                    <span className="font-medium leading-relaxed">{finding}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.sub_sections && section.sub_sections.length > 0 ? (
            <div className="flex flex-col gap-5 pt-2">
              <h3
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}
              >
                Detailed Breakdown
              </h3>
              <div className="grid gap-4">
                {section.sub_sections.map((sub, i) => (
                  <article
                    key={i}
                    className="flex flex-col gap-2 rounded-2xl border p-6 transition-colors hover:bg-[var(--surfaces-muted)]"
                    style={{ borderColor: 'var(--lines-subtle)' }}
                  >
                    <h4 className="text-lg font-bold text-[var(--text-primary)]">{sub.sub_section_name}</h4>
                    {typeof sub.analysis === 'string' ? (
                      <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                        {sub.analysis}
                      </p>
                    ) : (
                      <pre className="whitespace-pre-wrap text-xs text-[var(--text-secondary)]">
                        {JSON.stringify(sub.analysis, null, 2)}
                      </pre>
                    )}
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ))}
    </div>
  )
}
