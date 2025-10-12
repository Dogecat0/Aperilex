import { useThemeTokens } from '@/components/ThemeProvider'
import type { SubsectionPanelData } from '../types'
import { SubsectionDetailContent } from './subsections'
import { SubtleTag } from './subsections/shared'

export interface SubsectionDetailDrawerProps {
  open: boolean
  sectionName: string | null
  subsection: SubsectionPanelData | null
  onClose(): void
}

function pickDisplayString(value?: string | null) {
  if (typeof value !== 'string') {
    return null
  }

  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function formatKeyLabel(key: string) {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function SubsectionDetailDrawer({
  open,
  sectionName,
  subsection,
  onClose,
}: SubsectionDetailDrawerProps) {
  const tokens = useThemeTokens()

  if (!open || !subsection) {
    return null
  }

  const resolvedSectionName =
    pickDisplayString(sectionName) ??
    pickDisplayString(subsection.source.parent_section ?? null) ??
    subsection.name

  const schemaDisplay =
    subsection.schemaLabel ?? pickDisplayString(subsection.source.schema_type ?? null)
  const focusLabel = subsection.focus ? formatKeyLabel(subsection.focus) : null

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      style={{ background: 'rgba(15, 23, 42, 0.45)' }}
      role="dialog"
      aria-modal="true"
      aria-label="Subsection details"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <aside
        className="flex h-full w-full max-w-xl flex-col gap-4 border-l p-6"
        style={{
          borderColor: 'var(--lines-subtle)',
          background: 'var(--surfaces-muted)',
          boxShadow: tokens.shadows.strong,
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Section
              </p>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                {resolvedSectionName}
              </p>
            </div>
            <button
              type="button"
              className="text-xs font-semibold uppercase tracking-wide underline"
              style={{ color: tokens.metrics.stable }}
              onClick={onClose}
            >
              Close
            </button>
          </div>
          <div className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">{subsection.name}</h2>
            {subsection.synopsis ? (
              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                {subsection.synopsis}
              </p>
            ) : (
              <p className="text-sm italic text-[var(--text-muted)]">
                Synopsis not provided for this subsection.
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {focusLabel ? <SubtleTag>{focusLabel}</SubtleTag> : null}
            {schemaDisplay ? <SubtleTag>{schemaDisplay}</SubtleTag> : null}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4">
            <section className="flex flex-col gap-3 rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Key details
                </h3>
                {subsection.analysis ? (
                  <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                    {subsection.analysis.schemaType}
                  </span>
                ) : null}
              </div>
              {subsection.analysis ? (
                <SubsectionDetailContent analysis={subsection.analysis} />
              ) : (
                <p className="text-sm italic text-[var(--text-muted)]">
                  This subsection did not include structured fields beyond the synopsis.
                </p>
              )}
            </section>
          </div>
        </div>

        <footer className="flex flex-wrap justify-end gap-3">
          <button
            type="button"
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: tokens.metrics.stable }}
            onClick={onClose}
          >
            Close drawer
          </button>
        </footer>
      </aside>
    </div>
  )
}
