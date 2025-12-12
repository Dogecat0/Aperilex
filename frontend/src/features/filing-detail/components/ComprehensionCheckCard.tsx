import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { ComprehensionCheck } from '@/lib/types/analysis'

interface ComprehensionCheckCardProps {
  check: ComprehensionCheck
  completed: boolean
  onCompleted(): void
  onAttempt?(answer: string, isCorrect: boolean): void
}

type AnswerStatus = 'idle' | 'correct' | 'incorrect'

function createSeed(input: string) {
  let hash = 0
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash << 5) - hash + input.charCodeAt(index)
    hash |= 0
  }
  return hash >>> 0
}

function seededShuffle<T>(values: readonly T[], seedValue: string): T[] {
  const shuffled = [...values]
  if (shuffled.length <= 1) {
    return shuffled
  }

  let seed = createSeed(seedValue)
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    seed = (seed * 1664525 + 1013904223) % 4294967296
    const swapIndex = seed % (index + 1)
    ;[shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]]
  }

  return shuffled
}

export function ComprehensionCheckCard({
  check,
  completed,
  onCompleted,
  onAttempt,
}: ComprehensionCheckCardProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [status, setStatus] = useState<AnswerStatus>('idle')
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const correctBackground = useMemo(
    () => hexToRgba(tokens.status.positive, isLightMode ? 0.14 : 0.22),
    [isLightMode, tokens.status.positive]
  )
  const incorrectBackground = useMemo(
    () => hexToRgba(tokens.status.negative, isLightMode ? 0.14 : 0.22),
    [isLightMode, tokens.status.negative]
  )

  const distractorKey = useMemo(() => check.distractors.join('\u0000'), [check.distractors])

  const options = useMemo(() => {
    const ordered = [check.correct_answer, ...check.distractors]
    const seen = new Set<string>()
    const deduped = ordered.filter((option) => {
      if (seen.has(option)) {
        return false
      }
      seen.add(option)
      return true
    })

    const seedKey = `${check.id}::${check.correct_answer}::${distractorKey}`
    return seededShuffle(deduped, seedKey)
  }, [check.correct_answer, check.distractors, distractorKey, check.id])

  useEffect(() => {
    if (completed && status !== 'correct') {
      setStatus('correct')
    }
  }, [completed, status])

  function handleSelect(option: string) {
    if (completed) {
      return
    }

    setSelectedAnswer(option)
    const isCorrect = option === check.correct_answer
    if (onAttempt) {
      onAttempt(option, isCorrect)
    }

    if (isCorrect) {
      setStatus('correct')
      onCompleted()
    } else {
      setStatus('incorrect')
    }
  }

  const showExplanation = completed || status === 'correct'
  const showRetry = status === 'incorrect' && !completed

  return (
    <article
      className="rounded-2xl border p-5"
      style={{
        background: 'var(--surfaces-raised)',
        borderColor: 'var(--lines-subtle)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="mb-4">
        <p
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
        >
          Comprehension Check
        </p>
        <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{check.question}</h3>
      </header>

      <div className="flex flex-col gap-2">
        {options.map((option) => {
          const isSelected = selectedAnswer === option
          const isCorrectOption = option === check.correct_answer
          const resolvedCorrect = completed && isCorrectOption

          const borderColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? tokens.status.positive
              : isSelected && status === 'incorrect'
                ? tokens.status.negative
                : 'var(--lines-subtle)'
          const backgroundColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? correctBackground
              : isSelected && status === 'incorrect'
                ? incorrectBackground
                : 'var(--surfaces-base)'
          const textColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? tokens.status.positive
              : isSelected && status === 'incorrect'
                ? tokens.status.negative
                : 'var(--text-muted)'
          const hoverTextClass =
            textColor === 'var(--text-muted)' && !completed
              ? 'hover:text-[var(--text-primary)]'
              : ''

          return (
            <button
              key={option}
              type="button"
              onClick={() => handleSelect(option)}
              className={`rounded-xl border px-4 py-3 text-left text-sm text-[color:var(--option-text-color)] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)] ${hoverTextClass}`}
              style={
                {
                  borderColor,
                  backgroundColor,
                  '--option-text-color': textColor,
                  cursor: completed ? 'default' : 'pointer',
                } as CSSProperties
              }
              disabled={completed}
            >
              {option}
            </button>
          )
        })}
      </div>

      {showRetry ? (
        <p className="mt-3 text-sm" style={{ color: tokens.status.negative }}>
          Not quite. Select a different answer.
        </p>
      ) : null}

      {showExplanation ? (
        <div
          className="mt-4 rounded-xl p-4 text-sm"
          style={{
            background: 'var(--surfaces-muted)',
            color: 'var(--text-secondary)',
          }}
        >
          <p className="font-semibold text-[var(--text-primary)]">Explanation</p>
          <p className="mt-1 leading-relaxed">{check.explanation}</p>
        </div>
      ) : null}
    </article>
  )
}
