import { useEffect, useMemo, useState } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import type { SubsectionPanelData } from '../types'
import { SubsectionDetailContent } from './subsections'
import { SubtleTag } from './subsections/shared'

export interface SubsectionDetailDrawerProps {
  open: boolean
  sectionName: string | null
  subsection: SubsectionPanelData | null
  onClose(): void
  onJumpToRaw?(sectionName: string, subsection: SubsectionPanelData): void
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

function formatProcessingDuration(ms: number | null) {
  if (typeof ms !== 'number') {
    return 'Not captured'
  }

  if (ms < 1000) {
    return `${ms} ms`
  }

  const seconds = ms / 1000
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`
  }

  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return remainder < 1 ? `${minutes} min` : `${minutes} min ${Math.round(remainder)} s`
}

export function SubsectionDetailDrawer({
  open,
  sectionName,
  subsection,
  onClose,
  onJumpToRaw,
}: SubsectionDetailDrawerProps) {
  const tokens = useThemeTokens()
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    setShowRaw(false)
  }, [subsection?.id])

  const rawSource = useMemo(() => {
    if (!subsection) {
      return ''
    }

    try {
      return JSON.stringify(subsection.source, null, 2)
    } catch (error) {
      return `Failed to serialize subsection: ${(error as Error).message}`
    }
  }, [subsection])

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
            <span className="inline-flex items-center rounded-full bg-[var(--surfaces-raised)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Processing: {formatProcessingDuration(subsection.processingTimeMs ?? null)}
            </span>
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
              ) : subsection.rawAnalysis ? (
                <FallbackStructured payload={subsection.rawAnalysis} />
              ) : (
                <p className="text-sm italic text-[var(--text-muted)]">
                  This subsection did not include structured fields beyond the synopsis.
                </p>
              )}
            </section>

            <section className="flex flex-col gap-3 rounded-2xl border p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Raw subsection payload
                </h3>
                <button
                  type="button"
                  className="text-xs font-semibold uppercase tracking-wide underline"
                  style={{ color: tokens.metrics.stable }}
                  onClick={() => setShowRaw((prev) => !prev)}
                >
                  {showRaw ? 'Hide raw JSON' : 'Show raw JSON'}
                </button>
              </div>
              {showRaw ? (
                <pre className="max-h-64 overflow-auto rounded-2xl bg-[var(--surfaces-raised)] p-3 text-xs text-[var(--text-secondary)]">
                  {rawSource}
                </pre>
              ) : (
                <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                  Expand to inspect the original provider payload for this subsection.
                </p>
              )}
            </section>
          </div>
        </div>

        <footer className="flex flex-wrap justify-between gap-3">
          <button
            type="button"
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: tokens.metrics.up }}
            onClick={() => onJumpToRaw?.(resolvedSectionName, subsection)}
          >
            Jump to raw text
          </button>
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

function FallbackStructured({ payload }: { payload: unknown }) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return (
      <p className="text-sm italic text-[var(--text-muted)]">
        Structured fields were not provided for this subsection.
      </p>
    )
  }

  const entries = Object.entries(payload as Record<string, unknown>)
  if (entries.length === 0) {
    return (
      <p className="text-sm italic text-[var(--text-muted)]">
        Structured analysis returned an empty object.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-2 rounded-2xl bg-[var(--surfaces-raised)] p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {formatKeyLabel(key)}
          </p>
          {renderFallbackValue(value)}
        </div>
      ))}
    </div>
  )
}

function renderFallbackValue(value: unknown, depth = 0): JSX.Element {
  if (typeof value === 'string') {
    return <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{value}</p>
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return <p className="text-sm font-medium text-[var(--text-secondary)]">{String(value)}</p>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <p className="text-xs italic text-[var(--text-muted)]">Empty list</p>
    }

    if (value.every((item) => typeof item === 'string')) {
      return (
        <ul className="list-disc pl-5 text-sm leading-relaxed text-[var(--text-secondary)]">
          {value.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      )
    }

    return (
      <div className="flex flex-col gap-2">
        {value.map((entry, index) => (
          <div
            key={index}
            className="rounded-2xl border p-2"
            style={{ borderColor: 'var(--lines-subtle)' }}
          >
            {renderFallbackValue(entry, depth + 1)}
          </div>
        ))}
      </div>
    )
  }

  if (value && typeof value === 'object' && depth < 2) {
    const nested = Object.entries(value as Record<string, unknown>)
    if (nested.length === 0) {
      return <p className="text-xs italic text-[var(--text-muted)]">Empty object</p>
    }

    return (
      <div className="flex flex-col gap-2">
        {nested.map(([key, nestedValue]) => (
          <div key={key} className="flex flex-col gap-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {formatKeyLabel(key)}
            </p>
            {renderFallbackValue(nestedValue, depth + 1)}
          </div>
        ))}
      </div>
    )
  }

  try {
    return (
      <pre className="overflow-x-auto rounded-2xl bg-[var(--surfaces-muted)] p-3 text-xs text-[var(--text-secondary)]">
        {JSON.stringify(value, null, 2)}
      </pre>
    )
  } catch (error) {
    return <p className="text-xs italic text-[var(--text-muted)]">{String(error)}</p>
  }
}
