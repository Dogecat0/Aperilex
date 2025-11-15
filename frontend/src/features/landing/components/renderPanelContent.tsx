import type { HeroSlide } from '../content'

export function renderPanelContent(panel: HeroSlide['panel']) {
  switch (panel.type) {
    case 'launchpad':
      return (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
            {panel.heading}
          </p>
          <div className="rounded-2xl border border-white/15 bg-[var(--brand-background)]/20 p-4">
            <dl className="grid gap-3 sm:grid-cols-2">
              {panel.fields.map((field) => (
                <div key={field.label}>
                  <dt className="text-xs uppercase tracking-[0.25em] text-white/50">
                    {field.label}
                  </dt>
                  <dd className="pt-1 text-xs text-white/70">{field.helper}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="rounded-2xl border border-white/15 bg-[var(--brand-background)]/20 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-white/60">Templates</p>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {panel.templates.map((template) => (
                <article
                  key={template.name}
                  className="rounded-xl border border-white/15 bg-black/10 p-3 text-sm text-white/80"
                >
                  <h4 className="text-sm font-semibold text-white">{template.name}</h4>
                  <p className="pt-1 text-xs text-white/70">{template.helper}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      )
    case 'dashboard':
      return (
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
            {panel.heading}
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {panel.stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-white/15 bg-[var(--brand-background)]/20 p-3"
              >
                <p className="text-xs uppercase tracking-[0.25em] text-white/60">{stat.label}</p>
                <p className="pt-2 text-sm text-[var(text-on-muted)]">{stat.description}</p>
              </div>
            ))}
          </div>
          <div className="rounded-2xl border border-white/15 bg-[var(--brand-background)]/20 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-white/60">Filters</p>
            <div className="space-y-2 pt-3">
              {panel.filters.map((filter) => (
                <div
                  key={filter.label}
                  className="flex items-center justify-between text-sm text-white/80"
                >
                  <span className="text-white/60">{filter.label}</span>
                  <span>{filter.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )
    case 'saved':
      return (
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/60">
            {panel.heading}
          </p>
          <div className="space-y-5 rounded-2xl border border-white/15 bg-[var(--brand-background)]/20 p-4">
            {panel.entries.map((entry) => (
              <div key={entry.company} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-semibold text-white">{entry.company}</p>
                  <p className="text-white/60">{entry.label}</p>
                </div>
                <span className="text-xs text-white/60">{entry.reviewedAt}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-white/60">{panel.helper}</p>
        </div>
      )
    default:
      return null
  }
}
