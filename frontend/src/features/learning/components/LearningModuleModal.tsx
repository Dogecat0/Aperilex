import { Button } from '@/components/ui/Button'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import type {
  LearningProgressRecord,
  SectionProgressSnapshot,
} from '@/lib/hooks/useLearningProgress'

interface LearningModuleModalProps {
  module: LearningModule
  progress: LearningProgressRecord | null | undefined
  sectionProgress: SectionProgressSnapshot | null
  onClose: () => void
  onResume: () => Promise<void>
}

function formatDateLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Not reviewed yet'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Not reviewed yet'
  }

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function LearningModuleModal({
  module,
  progress,
  sectionProgress,
  onClose,
  onResume,
}: LearningModuleModalProps) {
  const resumeWalkthroughCta = module.ctas.find((cta) => cta.kind === 'walkthrough') ?? null
  const resumeDisabled = !resumeWalkthroughCta
  const resumeTitle = resumeDisabled
    ? 'Resume becomes available once the guided walkthrough is ready.'
    : undefined
  const progressPercent = sectionProgress?.progressPercent ?? progress?.progressPercent ?? 0
  const lastInteractionLabel = formatDateLabel(
    sectionProgress?.lastInteractionAt ?? progress?.lastInteractionAt ?? null
  )
  const completionTimestamp = sectionProgress?.completedAt ?? progress?.completedAt
  const completionLabel = completionTimestamp
    ? `Completed ${formatDateLabel(completionTimestamp)}`
    : 'Still in progress'

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[rgba(15,23,42,0.45)] px-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="learning-module-modal-title"
        className="relative flex w-full max-w-3xl flex-col gap-5 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-[var(--text-secondary)]">
              Module overview
            </p>
            <h2
              id="learning-module-modal-title"
              className="text-2xl font-semibold"
              style={{ letterSpacing: '-0.01em', color: 'var(--text-primary)' }}
            >
              {module.title}
            </h2>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">{module.summary}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold uppercase tracking-[0.26em] text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
          >
            Close
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-secondary)]">
              Progress
            </p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
              {progressPercent}%
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Last interaction {lastInteractionLabel}
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">{completionLabel}</p>
          </div>
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-secondary)]">
              Next steps
            </p>
            <p className="mt-2 text-sm text-[var(--text-secondary)] leading-6">
              Resume the guided walkthrough to keep context fresh and unlock the remaining guided
              prompts tied to your latest analysis.
            </p>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="mt-3 w-full"
              onClick={onResume}
              disabled={resumeDisabled}
              title={resumeTitle}
            >
              Resume walkthrough
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
