import { useThemeTokens } from '@/components/ThemeProvider'
import type { SectionAnalysis } from '@/lib/types/analysis'

interface RawSectionTabProps {
  sections: SectionAnalysis[]
}

export function RawSectionTab({ sections }: RawSectionTabProps) {
  const tokens = useThemeTokens()

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

  return (
    <div className="grid gap-6">
      {sections.map((section) => (
        <article
          key={section.section_name}
          className="rounded-3xl border p-6"
          style={{
            background: 'var(--surfaces-raised)',
            borderColor: 'var(--lines-subtle)',
            boxShadow: tokens.shadows.soft,
          }}
        >
          <header className="flex flex-col gap-1">
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
            >
              {section.sub_section_count ?? 0} subsections
            </p>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              {section.section_name}
            </h2>
            {section.section_summary ? (
              <p className="text-sm text-[var(--text-secondary)]">{section.section_summary}</p>
            ) : null}
          </header>

          {section.consolidated_insights && section.consolidated_insights.length > 0 ? (
            <div className="mt-4">
              <p
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
              >
                Insights
              </p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-[var(--text-secondary)]">
                {section.consolidated_insights.map((insight, index) => (
                  <li key={`${section.section_name}-insight-${index}`}>{insight}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.critical_findings && section.critical_findings.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--status-negative)]">
                Critical findings
              </p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-[var(--text-secondary)]">
                {section.critical_findings.map((finding, index) => (
                  <li key={`${section.section_name}-finding-${index}`}>{finding}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.sub_sections && section.sub_sections.length > 0 ? (
            <div className="mt-4 flex flex-col gap-3">
              <p
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
              >
                Subsections
              </p>
              {section.sub_sections.map((subSection) => (
                <div
                  key={subSection.sub_section_name}
                  className="rounded-2xl border bg-[var(--surfaces-muted)] p-4"
                  style={{ borderColor: 'var(--lines-subtle)' }}
                >
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {subSection.sub_section_name}
                  </p>
                  {typeof subSection.analysis === 'object' && subSection.analysis !== null ? (
                    <pre className="mt-2 whitespace-pre-wrap text-xs text-[var(--text-secondary)]">
                      {JSON.stringify(subSection.analysis, null, 2)}
                    </pre>
                  ) : null}
                  {typeof subSection.analysis === 'string' ? (
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">
                      {subSection.analysis}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  )
}
