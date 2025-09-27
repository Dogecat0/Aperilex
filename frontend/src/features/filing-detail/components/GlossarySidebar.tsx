import { Link } from 'react-router-dom'
import { glossaryEntries, type GlossaryEntry } from '@/lib/glossary'

export interface GlossarySidebarProps {
  entries?: GlossaryEntry[]
}

export function GlossarySidebar({ entries = glossaryEntries }: GlossarySidebarProps) {
  return (
    <aside
      className="flex flex-col gap-4 rounded-3xl border p-5"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
    >
      <header className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Glossary
        </p>
        <h2 className="text-base font-semibold text-[var(--colors-foreground)]">
          Filing fluency helpers
        </h2>
      </header>
      <ul className="flex flex-col gap-3 text-sm text-[var(--colors-foregroundMuted)]">
        {entries.map((entry) => (
          <li key={entry.term} className="flex flex-col gap-1">
            <p className="font-semibold text-[var(--colors-foreground)]">{entry.term}</p>
            <p>{entry.definition}</p>
            {entry.link ? (
              <Link
                to={entry.link}
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--colors-foreground)' }}
              >
                Explore in learning hub
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
    </aside>
  )
}
