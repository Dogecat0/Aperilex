import type { ThemeTokens } from '@/styles/tokens'
import type { ModuleAnalysisOption } from '@/lib/hooks'

export function formatTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Just now'
  }

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function parseNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }
  return null
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) {
    return '—'
  }

  if (seconds < 60) {
    return `${seconds}s`
  }

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes < 60) {
    return remainingSeconds ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h${remainingMinutes ? ` ${remainingMinutes}m` : ''}`
}

export function getMetadataNumber(
  metadata: Record<string, unknown> | undefined,
  key: string
): number | null {
  if (!metadata) {
    return null
  }
  return parseNumber(metadata[key])
}

export interface AttemptQuestionDetail {
  id: string
  question: string
  attempts: number
  incorrectAttempts: number
  firstAttemptAt: string | null
  lastAttemptAt: string | null
  completedAt: string | null
  userAnswer: string | null
  correctAnswer: string | null
}

export function normalizeAttemptResponses(
  responses: Record<string, unknown>
): AttemptQuestionDetail[] {
  const details: AttemptQuestionDetail[] = []

  for (const [questionId, raw] of Object.entries(responses)) {
    if (!raw || typeof raw !== 'object') {
      continue
    }
    const entry = raw as Record<string, unknown>

    const question =
      typeof entry.question === 'string' && entry.question.trim() ? entry.question : questionId
    const attempts = parseNumber(entry.attempts) ?? 0
    const incorrectAttempts =
      parseNumber(
        entry.incorrect_attempts ?? (entry as { incorrectAttempts?: unknown }).incorrectAttempts
      ) ?? 0
    const firstAttemptAt =
      typeof entry.first_attempt_at === 'string' ? entry.first_attempt_at : null
    const completedAt = typeof entry.completed_at === 'string' ? entry.completed_at : null
    const lastAttemptAt =
      typeof entry.last_attempt_at === 'string' ? entry.last_attempt_at : completedAt
    const userAnswer =
      typeof entry.final_answer === 'string'
        ? entry.final_answer
        : typeof entry.last_selected_option === 'string'
          ? entry.last_selected_option
          : null
    const correctAnswer = typeof entry.correct_answer === 'string' ? entry.correct_answer : null

    details.push({
      id: questionId,
      question,
      attempts,
      incorrectAttempts,
      firstAttemptAt,
      lastAttemptAt,
      completedAt,
      userAnswer,
      correctAnswer,
    })
  }

  return details.sort((a, b) => a.id.localeCompare(b.id))
}

export function describeAnalysisOption(option: ModuleAnalysisOption): string {
  const company = option.context?.companyName ?? 'Analysis'
  const filingType = option.context?.filingType ?? ''
  const filingDate = option.context?.filingDate
  const dateLabel =
    typeof filingDate === 'string' && filingDate
      ? new Date(filingDate).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
        })
      : null

  return [company, filingType, dateLabel].filter(Boolean).join(' · ')
}

export function getPreferredAnalysisId(
  metadata: Record<string, unknown> | undefined
): string | null {
  if (!metadata) {
    return null
  }

  const raw =
    metadata['preferred_analysis_id'] ??
    (metadata as { preferredAnalysisId?: unknown }).preferredAnalysisId
  if (typeof raw === 'string' && raw.trim()) {
    return raw
  }
  return null
}

export function describeSentiment(
  score: number | null,
  tokens: ThemeTokens
): { label: string; color: string } {
  if (typeof score !== 'number') {
    return { label: 'Sentiment pending', color: tokens.status.neutral }
  }

  const percent = Math.round(score * 100)
  if (score >= 0.15) {
    return { label: `Positive ${percent}%`, color: tokens.status.positive }
  }

  if (score <= -0.15) {
    return { label: `Negative ${Math.abs(percent)}%`, color: tokens.status.negative }
  }

  return { label: `Neutral ${percent}%`, color: tokens.status.neutral }
}

export function sentimentBadgeBackground(color: string): string {
  if (color.startsWith('#') && (color.length === 7 || color.length === 4)) {
    return `${color}1a`
  }

  return color
}
