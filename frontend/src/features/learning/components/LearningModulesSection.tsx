import { Button } from '@/components/ui/Button'
import type { ThemeTokens } from '@/styles/tokens'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import type { ModuleAnalysisOption } from '@/lib/hooks'
import type { SectionProgressSnapshot } from '@/lib/hooks/useLearningProgress'
import {
  describeAnalysisOption,
  describeSentiment,
  formatTimestamp,
  sentimentBadgeBackground,
} from './utils'

const MODULE_SKELETON_KEYS = ['module-a', 'module-b', 'module-c'] as const

interface LearningModulesSectionProps {
  modules: LearningModule[]
  isLoading: boolean
  moduleErrorMessage: string | null
  tokens: ThemeTokens
  analysisBinding: Record<string, string>
  onRetryModules: () => void
  onAnalysisChange: (module: LearningModule, analysisId: string) => void
  onResume: (module: LearningModule, option: ModuleAnalysisOption | null) => void
  getSectionProgressSnapshot: (
    moduleKey: string,
    sectionKey: string,
    analysisId?: string | null
  ) => SectionProgressSnapshot
}

function buildModuleOptions(module: LearningModule): ModuleAnalysisOption[] {
  if (module.analysisOptions.length > 0) {
    return module.analysisOptions
  }

  return [
    {
      optionId: `${module.key}::${module.context?.analysisId ?? 'latest'}`,
      cardKey: module.key,
      moduleKey: module.moduleKey,
      sectionKey: module.sectionKey,
      analysisId: module.context?.analysisId ?? '',
      title: module.title,
      duration: module.duration,
      summary: module.summary,
      focusTab: module.focusTab,
      focusSection: module.focusSection,
      context: module.context,
      ctas: module.ctas,
    },
  ]
}

function ModuleCard({
  module,
  tokens,
  analysisBinding,
  onAnalysisChange,
  onResume,
  getSectionProgressSnapshot,
}: Pick<
  LearningModulesSectionProps,
  'tokens' | 'analysisBinding' | 'onAnalysisChange' | 'onResume' | 'getSectionProgressSnapshot'
> & { module: LearningModule }) {
  const options = buildModuleOptions(module)
  const selectedAnalysisId =
    analysisBinding[module.moduleKey] ?? options[0]?.analysisId ?? module.context?.analysisId ?? ''
  const activeOption =
    options.find((option) => option.analysisId === selectedAnalysisId) ?? options[0] ?? null

  const context = activeOption?.context ?? module.context
  const sectionProgress = getSectionProgressSnapshot(
    module.moduleKey,
    activeOption?.sectionKey ?? module.sectionKey,
    activeOption?.analysisId ?? context?.analysisId ?? null
  )
  const moduleTitle = activeOption?.title ?? module.title
  const moduleDuration = activeOption?.duration ?? module.duration
  const progressPercent = sectionProgress.progressPercent
  const statusLabel =
    sectionProgress.status === 'completed'
      ? 'Completed'
      : sectionProgress.status === 'in_progress'
        ? 'In progress'
        : 'Queued'
  const accentColor =
    sectionProgress.status === 'completed'
      ? tokens.status.positive
      : sectionProgress.status === 'in_progress'
        ? tokens.learning.accent
        : tokens.status.neutral
  const hasContext = Boolean(context)
  const sentimentBadge = context
    ? describeSentiment(
        typeof context.sentimentScore === 'number' ? context.sentimentScore : null,
        tokens
      )
    : null
  const guidanceFocus = context?.guidanceFocus?.trim()
  const guidanceWhy = context?.guidanceWhyItMatters?.trim()
  const resumeDisabled = !hasContext
  const resumeLabel = progressPercent >= 100 ? 'Review walkthrough' : 'Resume walkthrough'
  const resumeTitle = !hasContext
    ? 'Launch a filing analysis to unlock contextual practice.'
    : undefined

  return (
    <article
      key={module.key}
      className="group flex w-full flex-col gap-6 rounded-3xl border px-6 py-6 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg md:flex-row md:gap-8"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <div className="flex flex-col gap-4 md:flex-[2] md:justify-center">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span
              className="text-[11px] font-bold uppercase tracking-[0.2em]"
              style={{ color: accentColor }}
            >
              {statusLabel}
            </span>
            <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
              {moduleDuration}
            </span>
          </div>
          <h3
            className="text-2xl font-bold"
            style={{
              color: 'var(--text-primary)',
              letterSpacing: tokens.typography.letterSpacing.tight,
            }}
          >
            {moduleTitle}
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className="text-[11px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: 'var(--text-secondary)' }}
          >
            Analysis source
          </span>
          <select
            value={activeOption?.analysisId ?? ''}
            onChange={(event) => onAnalysisChange(module, event.target.value)}
            className="rounded-lg border border-[var(--lines-subtle)] bg-transparent px-3 py-1 text-xs text-[var(--text-primary)]"
          >
            {options.map((option) => (
              <option key={option.optionId} value={option.analysisId}>
                {describeAnalysisOption(option)}
              </option>
            ))}
          </select>
        </div>

        {context ? (
          <div
            className="flex flex-col gap-3 rounded-2xl border px-5 py-4 text-sm transition-colors group-hover:border-[var(--lines-strong)]"
            style={{
              borderColor: 'var(--surfaces-base)',
              background: 'var(--surfaces-muted)',
            }}
          >
            {context.highlight && (
              <p
                className="text-sm font-medium"
                style={{
                  color: 'var(--text-primary)',
                  lineHeight: '1.6',
                }}
              >
                {context.highlight}
              </p>
            )}
            {(guidanceFocus || guidanceWhy) && (
              <div className="space-y-3 mt-1 text-[var(--text-secondary)]">
                {guidanceFocus && (
                  <p>
                    <span className="font-semibold text-[var(--text-primary)]">Focus:</span>{' '}
                    {guidanceFocus}
                  </p>
                )}
                {guidanceWhy && (
                  <p>
                    <span className="font-semibold text-[var(--text-primary)]">
                      Why it matters:
                    </span>{' '}
                    {guidanceWhy}
                  </p>
                )}
              </div>
            )}
            {context.previousComparison?.pro_tip && (
              <div className="mt-2 flex items-start gap-2 text-[var(--text-secondary)]">
                <span className="text-lg">💡</span>
                <p className="text-sm italic">
                  {`${context.previousComparison.pro_tip} Resume the walkthrough for more details.`}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div
            className="rounded-xl border border-dashed px-4 py-3 text-center"
            style={{ borderColor: 'var(--lines-subtle)' }}
          >
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              Run a completed filing analysis to unlock contextual practice material.
            </p>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-4 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/70 md:pl-8">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex flex-col gap-1">
            <span
              className="text-[11px] font-bold uppercase tracking-[0.2em]"
              style={{ color: 'var(--text-secondary)' }}
            >
              Activity
            </span>
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {sectionProgress.lastInteractionAt
                ? `Last active ${formatTimestamp(sectionProgress.lastInteractionAt)}`
                : 'Not started yet'}
            </span>
          </div>
          {sentimentBadge && (
            <span
              className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
              style={{
                background: sentimentBadgeBackground(sentimentBadge.color),
                color: sentimentBadge.color,
              }}
            >
              {sentimentBadge.label}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-2 mt-2">
          <div className="flex justify-between items-end">
            <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Progress
            </span>
            <span className="text-sm font-medium" style={{ color: accentColor }}>
              {progressPercent}%
            </span>
          </div>
          <div
            aria-label={`Progress ${progressPercent}%`}
            className="h-2.5 overflow-hidden rounded-full"
            style={{ background: 'var(--surfaces-muted)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%`, background: accentColor }}
            />
          </div>
        </div>

        <div className="mt-auto pt-4">
          <Button
            type="button"
            size="md"
            variant="primary"
            onClick={() => onResume(module, activeOption)}
            disabled={resumeDisabled}
            title={resumeTitle}
            className="w-full shadow-md transition-transform active:scale-95"
            style={resumeDisabled ? { boxShadow: 'none' } : undefined}
          >
            {resumeLabel}
          </Button>
        </div>
      </div>
    </article>
  )
}

export function LearningModulesSection({
  modules,
  isLoading,
  moduleErrorMessage,
  tokens,
  analysisBinding,
  onRetryModules,
  onAnalysisChange,
  onResume,
  getSectionProgressSnapshot,
}: LearningModulesSectionProps) {
  const showSkeletons = isLoading && modules.length === 0
  const showModules = showSkeletons || modules.length > 0

  return (
    <section
      className="flex flex-col gap-6"
      aria-busy={isLoading && modules.length === 0}
      aria-label="Learning modules"
    >
      {moduleErrorMessage && (
        <div
          className="flex flex-col gap-2 rounded-xl border px-4 py-3 text-sm backdrop-blur-sm"
          style={{
            borderColor: tokens.status.negative,
            background: 'rgba(231, 92, 74, 0.12)',
            color: tokens.status.negative,
          }}
        >
          <span>{moduleErrorMessage}</span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRetryModules}
            className="self-start px-0"
            style={{ color: tokens.status.negative }}
          >
            Retry loading modules
          </Button>
        </div>
      )}

      {!isLoading && modules.length === 0 && !moduleErrorMessage ? (
        <div
          className="rounded-3xl border px-6 py-8 text-center text-sm backdrop-blur-sm"
          style={{
            borderColor: 'var(--lines-subtle)',
            background: 'var(--surfaces-muted)',
            color: 'var(--text-secondary)',
            lineHeight: 'var(--typography-line-heights-standard)',
          }}
        >
          Launch a filing analysis from the dashboard to unlock Stage 5 personalized practice
          modules anchored to real insights.
        </div>
      ) : null}

      {showModules ? (
        <div className="flex flex-col gap-6">
          {showSkeletons
            ? MODULE_SKELETON_KEYS.map((placeholderKey) => (
                <article
                  key={placeholderKey}
                  className="flex w-full flex-col gap-4 rounded-3xl border px-6 py-6 animate-pulse md:flex-row md:gap-8"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-raised)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <div className="flex flex-col gap-4 md:flex-[2] md:justify-center">
                    <div className="flex flex-col gap-3">
                      <span className="h-3 w-24 rounded-full bg-[var(--lines-subtle)]/50" />
                      <span className="h-8 w-3/4 rounded-full bg-[var(--lines-subtle)]/50" />
                    </div>
                    <div className="space-y-3">
                      <span className="block h-3 w-full rounded-full bg-[var(--lines-subtle)]/40" />
                      <span className="block h-3 w-2/3 rounded-full bg-[var(--lines-subtle)]/40" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-4 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/60 md:pl-8">
                    <span className="h-3 w-16 rounded-full bg-[var(--lines-subtle)]/40" />
                    <div className="h-2 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                    <span className="h-3 w-1/2 rounded-full bg-[var(--lines-subtle)]/30" />
                  </div>
                </article>
              ))
            : modules.map((module) => (
                <ModuleCard
                  key={module.key}
                  module={module}
                  tokens={tokens}
                  analysisBinding={analysisBinding}
                  onAnalysisChange={onAnalysisChange}
                  onResume={onResume}
                  getSectionProgressSnapshot={getSectionProgressSnapshot}
                />
              ))}
        </div>
      ) : null}
    </section>
  )
}
