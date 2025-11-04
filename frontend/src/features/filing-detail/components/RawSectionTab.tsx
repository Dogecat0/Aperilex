import type { SectionAnalysis } from '@/lib/types/analysis'

interface RawSectionTabProps {
  sections: SectionAnalysis[]
}

export function RawSectionTab({ sections }: RawSectionTabProps) {
  if (!sections || sections.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
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
          className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <header className="flex flex-col gap-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {section.sub_section_count ?? 0} subsections
            </p>
            <h2 className="text-lg font-semibold text-slate-900">{section.section_name}</h2>
            {section.section_summary ? (
              <p className="text-sm text-slate-600">{section.section_summary}</p>
            ) : null}
          </header>

          {section.consolidated_insights && section.consolidated_insights.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Insights
              </p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-700">
                {section.consolidated_insights.map((insight, index) => (
                  <li key={`${section.section_name}-insight-${index}`}>{insight}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.critical_findings && section.critical_findings.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-rose-600">
                Critical findings
              </p>
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-700">
                {section.critical_findings.map((finding, index) => (
                  <li key={`${section.section_name}-finding-${index}`}>{finding}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {section.sub_sections && section.sub_sections.length > 0 ? (
            <div className="mt-4 flex flex-col gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Subsections
              </p>
              {section.sub_sections.map((subSection) => (
                <div
                  key={subSection.sub_section_name}
                  className="rounded-2xl border border-slate-100 bg-slate-50 p-4"
                >
                  <p className="text-sm font-semibold text-slate-800">
                    {subSection.sub_section_name}
                  </p>
                  {typeof subSection.analysis === 'object' && subSection.analysis !== null ? (
                    <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-600">
                      {JSON.stringify(subSection.analysis, null, 2)}
                    </pre>
                  ) : null}
                  {typeof subSection.analysis === 'string' ? (
                    <p className="mt-2 text-sm text-slate-600">{subSection.analysis}</p>
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
