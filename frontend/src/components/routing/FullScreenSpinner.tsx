import type { CSSProperties } from 'react'

const containerStyles: CSSProperties = {
  minHeight: '100vh',
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--colors-background)',
  padding: '1.5rem',
}

export function FullScreenSpinner() {
  return (
    <div style={containerStyles} data-testid="full-screen-spinner">
      <div
        role="status"
        aria-live="polite"
        className="flex flex-col items-center gap-4"
        style={{ color: 'var(--colors-foregroundMuted)' }}
      >
        <span
          className="inline-flex h-12 w-12 animate-spin rounded-full border-4"
          style={{
            borderColor: 'rgba(148, 163, 184, 0.35)',
            borderTopColor: 'var(--sentiment-neutral)',
          }}
        />
        <p className="text-sm font-medium">Checking your session…</p>
      </div>
    </div>
  )
}

export default FullScreenSpinner
