import { useEffect, useMemo, useState } from 'react'
import type { ComprehensionCheck } from '@/lib/types/analysis'

interface ComprehensionCheckCardProps {
  check: ComprehensionCheck
  completed: boolean
  onCompleted(): void
}

type AnswerStatus = 'idle' | 'correct' | 'incorrect'

export function ComprehensionCheckCard({
  check,
  completed,
  onCompleted,
}: ComprehensionCheckCardProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const [status, setStatus] = useState<AnswerStatus>('idle')

  const options = useMemo(() => {
    const ordered = [check.correct_answer, ...check.distractors]
    const seen = new Set<string>()
    return ordered.filter((option) => {
      if (seen.has(option)) {
        return false
      }
      seen.add(option)
      return true
    })
  }, [check.correct_answer, check.distractors])

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
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Comprehension Check
        </p>
        <h3 className="mt-1 text-lg font-semibold text-slate-900">{check.question}</h3>
      </header>

      <div className="flex flex-col gap-2">
        {options.map((option) => {
          const isSelected = selectedAnswer === option
          const isCorrectOption = option === check.correct_answer
          const resolvedCorrect = completed && isCorrectOption

          const borderColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? 'rgb(34 197 94)'
              : isSelected && status === 'incorrect'
                ? 'rgb(248 113 113)'
                : 'var(--lines-subtle, rgb(226 232 240))'
          const backgroundColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? 'rgb(240 253 244)'
              : isSelected && status === 'incorrect'
                ? 'rgb(254 242 242)'
                : 'white'
          const textColor =
            resolvedCorrect || (isSelected && status === 'correct')
              ? 'rgb(22 101 52)'
              : isSelected && status === 'incorrect'
                ? 'rgb(185 28 28)'
                : 'rgb(15 23 42)'

          return (
            <button
              key={option}
              type="button"
              onClick={() => handleSelect(option)}
              className="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
              style={{
                borderColor,
                backgroundColor,
                color: textColor,
                cursor: completed ? 'default' : 'pointer',
              }}
              disabled={completed}
            >
              {option}
            </button>
          )
        })}
      </div>

      {showRetry ? (
        <p className="mt-3 text-sm text-rose-600">Not quite. Select a different answer.</p>
      ) : null}

      {showExplanation ? (
        <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">Explanation</p>
          <p className="mt-1 leading-relaxed">{check.explanation}</p>
        </div>
      ) : null}
    </article>
  )
}
