import { Link } from 'react-router-dom'

export function FirstRunLaunchpad() {
  return (
    <section
      className="flex flex-col gap-6 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
          First-run launchpad
        </p>
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">
          You’re one analysis away from populating this dashboard
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Use the analysis workspace to search your filings, queue an AI run, and return here to see
          summaries, sentiment, and guided learning prompts.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          {
            title: 'Search a company',
            description: 'Locate a recent 10-K or 10-Q that matters to your learning journey.',
          },
          {
            title: 'Queue the analysis',
            description:
              'We’ll fetch the filing content, run the LLM workflow, and track progress.',
          },
          {
            title: 'Review insights',
            description:
              'Come back to the dashboard for summaries, sentiment, and practice prompts.',
          },
        ].map((item) => (
          <div
            key={item.title}
            className="rounded-2xl border p-4"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
          >
            <p className="text-sm font-semibold text-[var(--text-primary)]">{item.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
              {item.description}
            </p>
          </div>
        ))}
      </div>

      <div>
        <Link
          to="/analyze"
          className="inline-flex items-center justify-center rounded-full bg-[var(--status-positive)] px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white"
        >
          Open analysis launchpad
        </Link>
      </div>
    </section>
  )
}
