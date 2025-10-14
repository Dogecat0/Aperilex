import { useEffect, useMemo, useState } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import type { SentimentTone, SubsectionPanelData } from '../types'
import type {
  CashPosition,
  DebtLevel,
  LiquidityPosition,
  OutlookSentiment,
  RiskSeverity,
} from '@/lib/types/analysisSchemas'

export interface SectionSummaryPanelProps {
  sectionName: string
  tone: SentimentTone
  sentiment?: number | null
  summary?: string | null
  insights?: string[]
  criticalFindings?: string[]
  subsections?: SubsectionPanelData[]
  onExplain?(sectionName: string): void
  onSelectSubsection?(sectionName: string, subsection: SubsectionPanelData): void
}

function buildBaseChips(subsection: SubsectionPanelData): SummaryChip[] {
  const chips: SummaryChip[] = []

  if (subsection.focus) {
    const focusLabel = humanizeLabel(subsection.focus)
    if (focusLabel) {
      chips.push({
        id: `${subsection.id}-focus`,
        text: focusLabel,
        tone: 'neutral',
      })
    }
  }

  if (subsection.schemaLabel) {
    const schemaLabel = humanizeLabel(subsection.schemaLabel)
    if (schemaLabel) {
      chips.push({
        id: `${subsection.id}-schema`,
        text: schemaLabel,
        tone: 'neutral',
      })
    }
  }

  return chips
}

function buildHighlightChips(subsection: SubsectionPanelData): SummaryChip[] {
  const analysis = subsection.analysis
  if (!analysis) {
    return []
  }

  const chips: SummaryChip[] = []

  switch (analysis.schemaType) {
    case 'OperationalOverview': {
      chips.push({
        id: `${subsection.id}-industry`,
        text: analysis.data.industry_classification,
        tone: 'neutral',
      })

      if (analysis.data.primary_markets.length > 0) {
        chips.push({
          id: `${subsection.id}-markets`,
          text: `${analysis.data.primary_markets.length} markets`,
          tone: 'notice',
        })
      }
      break
    }
    case 'BusinessSegmentAnalysis': {
      chips.push({
        id: `${subsection.id}-segment-type`,
        text: analysis.data.segment_type,
        tone: 'neutral',
      })

      if (analysis.data.growth_outlook) {
        chips.push({
          id: `${subsection.id}-growth`,
          text: truncateLabel(analysis.data.growth_outlook, 36),
          tone: 'notice',
        })
      }
      break
    }
    case 'GeographicSegmentAnalysis': {
      chips.push({
        id: `${subsection.id}-region`,
        text: analysis.data.region,
        tone: 'neutral',
      })
      break
    }
    case 'BusinessAnalysisSection': {
      chips.push({
        id: `${subsection.id}-products`,
        text: `Products ${analysis.data.key_products.length}`,
        tone: 'notice',
      })
      chips.push({
        id: `${subsection.id}-segments`,
        text: `Segments ${analysis.data.business_segments.length}`,
        tone: 'notice',
      })
      break
    }
    case 'RiskFactor': {
      chips.push({
        id: `${subsection.id}-severity`,
        text: `${analysis.data.severity} risk`,
        tone: toneForSeverity(analysis.data.severity),
      })

      if (analysis.data.probability) {
        chips.push({
          id: `${subsection.id}-probability`,
          text: `Probability ${analysis.data.probability}`,
          tone: 'notice',
        })
      }
      break
    }
    case 'RiskFactorsAnalysisSection': {
      chips.push({
        id: `${subsection.id}-risk-count`,
        text: `Risks ${analysis.data.risk_factors.length}`,
        tone: 'notice',
      })
      break
    }
    case 'FinancialMetric': {
      chips.push({
        id: `${subsection.id}-direction`,
        text: formatDirection(analysis.data.direction),
        tone: toneForDirection(analysis.data.direction),
      })

      if (analysis.data.percentage_change) {
        chips.push({
          id: `${subsection.id}-delta`,
          text: analysis.data.percentage_change,
          tone: 'notice',
        })
      }
      break
    }
    case 'FinancialRatio': {
      const current = formatChipNumber(analysis.data.current_value)
      if (current) {
        chips.push({
          id: `${subsection.id}-ratio-current`,
          text: `Now ${current}`,
          tone: 'neutral',
        })
      }

      const benchmark = formatChipNumber(analysis.data.industry_benchmark)
      if (benchmark) {
        chips.push({
          id: `${subsection.id}-ratio-benchmark`,
          text: `Benchmark ${benchmark}`,
          tone: 'notice',
        })
      }
      break
    }
    case 'CashFlowRatio': {
      const current = formatChipNumber(analysis.data.current_value)
      if (current) {
        chips.push({
          id: `${subsection.id}-cashflow-ratio`,
          text: `Now ${current}`,
          tone: 'neutral',
        })
      }
      break
    }
    case 'RevenueSegment': {
      if (analysis.data.growth_rate) {
        chips.push({
          id: `${subsection.id}-segment-growth`,
          text: `Growth ${analysis.data.growth_rate}`,
          tone: 'notice',
        })
      }

      const share = formatChipPercentage(analysis.data.percentage_of_total)
      if (share) {
        chips.push({
          id: `${subsection.id}-segment-share`,
          text: `Share ${share}`,
          tone: 'neutral',
        })
      }
      break
    }
    case 'ExpenseCategory': {
      if (analysis.data.year_over_year_change) {
        chips.push({
          id: `${subsection.id}-expense-change`,
          text: `YoY ${analysis.data.year_over_year_change}`,
          tone: 'notice',
        })
      }
      break
    }
    case 'ProfitabilityMetric': {
      const margin = formatChipPercentage(analysis.data.margin_percentage)
      if (margin) {
        chips.push({
          id: `${subsection.id}-metric-margin`,
          text: `Margin ${margin}`,
          tone: 'neutral',
        })
      }
      break
    }
    case 'OperatingCashFlow': {
      const conversion = formatChipNumber(analysis.data.cash_conversion_ratio)
      if (conversion) {
        chips.push({
          id: `${subsection.id}-conversion`,
          text: `Conversion ${conversion}`,
          tone: 'notice',
        })
      }
      break
    }
    case 'InvestingCashFlow': {
      if (analysis.data.net_cash_from_investing) {
        chips.push({
          id: `${subsection.id}-investing-net`,
          text: truncateLabel(analysis.data.net_cash_from_investing, 32),
          tone: 'neutral',
        })
      }
      break
    }
    case 'FinancingCashFlow': {
      if (analysis.data.net_cash_from_financing) {
        chips.push({
          id: `${subsection.id}-financing-net`,
          text: truncateLabel(analysis.data.net_cash_from_financing, 32),
          tone: 'neutral',
        })
      }
      break
    }
    case 'BalanceSheetAnalysisSection': {
      chips.push({
        id: `${subsection.id}-liquidity`,
        text: `Liquidity ${analysis.data.liquidity_position}`,
        tone: toneForLiquidity(analysis.data.liquidity_position),
      })
      chips.push({
        id: `${subsection.id}-debt`,
        text: `Debt ${analysis.data.debt_level}`,
        tone: toneForDebtLevel(analysis.data.debt_level),
      })
      chips.push({
        id: `${subsection.id}-trend`,
        text: formatTrend(analysis.data.overall_trend),
        tone: toneForTrend(analysis.data.overall_trend),
      })
      break
    }
    case 'IncomeStatementAnalysisSection': {
      chips.push({
        id: `${subsection.id}-revenue-trend`,
        text: formatTrend(analysis.data.revenue_trend),
        tone: toneForTrend(analysis.data.revenue_trend),
      })
      chips.push({
        id: `${subsection.id}-profitability`,
        text: `Profitability ${analysis.data.profitability_level}`,
        tone: toneForProfitabilityLevel(analysis.data.profitability_level),
      })
      break
    }
    case 'CashFlowAnalysisSection': {
      chips.push({
        id: `${subsection.id}-cash-position`,
        text: `Cash ${analysis.data.cash_position}`,
        tone: toneForCashPosition(analysis.data.cash_position),
      })
      chips.push({
        id: `${subsection.id}-cash-trend`,
        text: formatTrend(analysis.data.cash_flow_trend),
        tone: toneForTrend(analysis.data.cash_flow_trend),
      })
      break
    }
    case 'MDAAnalysisSection': {
      chips.push({
        id: `${subsection.id}-outlook`,
        text: `Outlook ${analysis.data.outlook_sentiment}`,
        tone: toneForSentiment(analysis.data.outlook_sentiment),
      })

      chips.push({
        id: `${subsection.id}-metrics-count`,
        text: `Metrics ${analysis.data.key_financial_metrics.length}`,
        tone: 'notice',
      })
      break
    }
    case 'ForwardLookingStatement': {
      chips.push({
        id: `${subsection.id}-metric-area`,
        text: `Focus ${analysis.data.metric_area}`,
        tone: 'notice',
      })
      break
    }
    default:
      break
  }

  return chips
}

function formatChipNumber(value?: number | null) {
  if (value === null || value === undefined) {
    return null
  }

  return CHIP_NUMBER_FORMATTER.format(value)
}

function formatChipPercentage(value?: number | null) {
  const numeric = formatChipNumber(value)
  return numeric ? `${numeric}%` : null
}

function toneForDirection(direction: string): ChipTone {
  switch (direction) {
    case 'Increased':
      return 'positive'
    case 'Decreased':
      return 'negative'
    case 'Volatile':
      return 'notice'
    case 'Stable':
    default:
      return 'neutral'
  }
}

function formatDirection(direction: string) {
  switch (direction) {
    case 'Increased':
      return '↑ Increased'
    case 'Decreased':
      return '↓ Decreased'
    case 'Volatile':
      return '~ Volatile'
    case 'Stable':
    default:
      return '→ Stable'
  }
}

function toneForSeverity(severity: RiskSeverity): ChipTone {
  switch (severity) {
    case 'Critical':
    case 'High':
      return 'negative'
    case 'Medium':
      return 'notice'
    case 'Low':
    default:
      return 'neutral'
  }
}

function toneForLiquidity(position: LiquidityPosition): ChipTone {
  switch (position) {
    case 'Strong':
      return 'positive'
    case 'Adequate':
      return 'neutral'
    case 'Weak':
    case 'Critical':
      return 'negative'
    default:
      return 'notice'
  }
}

function toneForDebtLevel(level: DebtLevel): ChipTone {
  switch (level) {
    case 'Low':
      return 'positive'
    case 'Moderate':
      return 'neutral'
    case 'High':
    case 'Excessive':
      return 'negative'
    default:
      return 'notice'
  }
}

function toneForCashPosition(position: CashPosition): ChipTone {
  switch (position) {
    case 'Strong':
      return 'positive'
    case 'Adequate':
      return 'neutral'
    case 'Tight':
      return 'notice'
    case 'Critical':
      return 'negative'
    default:
      return 'notice'
  }
}

function toneForSentiment(sentiment: OutlookSentiment): ChipTone {
  switch (sentiment) {
    case 'Positive':
    case 'Optimistic':
      return 'positive'
    case 'Negative':
      return 'negative'
    case 'Cautious':
      return 'notice'
    case 'Neutral':
    default:
      return 'neutral'
  }
}

function toneForTrend(value: string): ChipTone {
  switch (value) {
    case 'Improving':
    case 'Growing':
      return 'positive'
    case 'Declining':
      return 'negative'
    case 'Volatile':
      return 'notice'
    case 'Stable':
    default:
      return 'neutral'
  }
}

function formatTrend(value: string) {
  switch (value) {
    case 'Improving':
    case 'Growing':
      return '↑ ' + value
    case 'Declining':
      return '↓ ' + value
    case 'Volatile':
      return '~ ' + value
    case 'Stable':
    default:
      return '→ ' + value
  }
}

function toneForProfitabilityLevel(level: string): ChipTone {
  switch (level) {
    case 'Excellent':
    case 'Good':
      return 'positive'
    case 'Fair':
      return 'notice'
    case 'Poor':
      return 'negative'
    default:
      return 'neutral'
  }
}

function truncateLabel(value: string, limit = 40) {
  const trimmed = value.trim()
  if (trimmed.length <= limit) {
    return trimmed
  }

  return `${trimmed.slice(0, limit - 3)}...`
}

function formatSentiment(value?: number | null) {
  if (typeof value !== 'number') {
    return 'n/a'
  }

  return `${(value * 100).toFixed(0)}%`
}

function toTitleCase(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter((segment) => segment.length > 0)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

const CHIP_NUMBER_FORMATTER = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
})

type ChipTone = 'positive' | 'negative' | 'neutral' | 'notice'

interface SummaryChip {
  id: string
  text: string
  tone: ChipTone
}

function humanizeLabel(raw: string): string {
  const withSpaces = raw
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
  if (withSpaces.length === 0) {
    return ''
  }

  return withSpaces
    .split(' ')
    .filter((segment) => segment.length > 0)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ')
}

function normalizeChipText(text: string): string {
  return text.replace(/[\s_-]+/g, '').toLowerCase()
}

function dedupeChips(chips: SummaryChip[]): SummaryChip[] {
  const seen = new Set<string>()
  const result: SummaryChip[] = []

  for (const chip of chips) {
    const normalized = normalizeChipText(chip.text)
    if (!normalized || seen.has(normalized)) {
      continue
    }
    seen.add(normalized)
    result.push(chip)
  }

  return result
}

export function SectionSummaryPanel({
  sectionName,
  tone,
  sentiment,
  summary,
  insights,
  criticalFindings,
  subsections,
  onExplain,
  onSelectSubsection,
}: SectionSummaryPanelProps) {
  const tokens = useThemeTokens()
  const [showSubsections, setShowSubsections] = useState(false)
  const [focusFilter, setFocusFilter] = useState<string | null>(null)

  const hasSubsections = Boolean(subsections && subsections.length > 0)

  const focusOptions = useMemo(() => {
    if (!subsections) {
      return []
    }

    const values = new Set<string>()
    for (const item of subsections) {
      if (item.focus) {
        values.add(item.focus)
      }
    }

    return Array.from(values).sort((a, b) => a.localeCompare(b))
  }, [subsections])

  const handleToggleSubsections = () => {
    setShowSubsections((prev) => !prev)
  }

  const filteredSubsections = useMemo(() => {
    if (!subsections || subsections.length === 0) {
      return []
    }

    if (!focusFilter) {
      return subsections
    }

    return subsections.filter((item) => item.focus === focusFilter)
  }, [focusFilter, subsections])

  useEffect(() => {
    if (focusFilter && !focusOptions.includes(focusFilter)) {
      setFocusFilter(null)
    }
  }, [focusFilter, focusOptions])

  useEffect(() => {
    if (showSubsections) {
      onExplain?.(sectionName)
      return
    }

    if (focusFilter !== null) {
      setFocusFilter(null)
    }
  }, [focusFilter, onExplain, sectionName, showSubsections])

  const toneColor =
    tone === 'positive'
      ? tokens.status.positive
      : tone === 'negative'
        ? tokens.status.negative
        : tokens.status.neutral

  const renderChip = (chip: SummaryChip) => {
    const baseClass =
      'inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide'

    if (chip.tone === 'neutral') {
      return (
        <span
          key={chip.id}
          className={baseClass}
          style={{
            borderColor: 'var(--lines-subtle)',
            borderWidth: 1,
            borderStyle: 'solid',
            background: 'var(--surfaces-muted)',
            color: 'var(--text-secondary)',
          }}
        >
          {chip.text}
        </span>
      )
    }

    const background =
      chip.tone === 'positive'
        ? tokens.status.positive
        : chip.tone === 'negative'
          ? tokens.status.negative
          : tokens.metrics.up

    return (
      <span
        key={chip.id}
        className={baseClass}
        style={{
          background,
          color: '#0f172a',
        }}
      >
        {chip.text}
      </span>
    )
  }

  return (
    <article
      className="flex flex-col gap-4 rounded-3xl border p-5"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-muted)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
              style={{ background: toneColor, color: '#0f172a' }}
            >
              {tone}
            </span>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {sectionName}
            </p>
            {hasSubsections ? (
              <span className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Subsections: {subsections?.length ?? 0}
              </span>
            ) : null}
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            Sentiment: {formatSentiment(sentiment)}
          </p>
        </div>
        {summary ? (
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{summary}</p>
        ) : (
          <p className="text-sm italic text-[var(--text-secondary)]">
            Summary not provided for this section.
          </p>
        )}
      </header>

      {insights && insights.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Key insights
          </h3>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-muted)]">
            {insights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {criticalFindings && criticalFindings.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Critical findings
          </h3>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-muted)]">
            {criticalFindings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {hasSubsections ? (
        <section className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="text-xs font-semibold uppercase tracking-wide underline"
                style={{ color: tokens.metrics.up }}
                onClick={handleToggleSubsections}
              >
                {showSubsections ? 'Hide details' : 'Explain more'}
              </button>
              {focusOptions.length > 0 && showSubsections ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors"
                    style={{
                      borderColor:
                        focusFilter === null ? tokens.metrics.stable : 'var(--lines-subtle)',
                      background:
                        focusFilter === null ? tokens.metrics.stable : 'var(--surfaces-muted)',
                      color: focusFilter === null ? '#0f172a' : 'var(--text-secondary)',
                    }}
                    onClick={() => setFocusFilter(null)}
                  >
                    All
                  </button>
                  {focusOptions.map((focusValue) => {
                    const isActive = focusFilter === focusValue
                    const displayFocus = humanizeLabel(focusValue)
                    return (
                      <button
                        key={focusValue}
                        type="button"
                        className="rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors"
                        style={{
                          borderColor: isActive ? tokens.metrics.up : 'var(--lines-subtle)',
                          background: isActive ? tokens.metrics.up : 'var(--surfaces-muted)',
                          color: isActive ? '#0f172a' : 'var(--text-secondary)',
                        }}
                        onClick={() => setFocusFilter(isActive ? null : focusValue)}
                      >
                        {displayFocus || toTitleCase(focusValue)}
                      </button>
                    )
                  })}
                </div>
              ) : null}
            </div>
            <span className="text-xs font-medium text-[var(--text-muted)]">
              Showing {filteredSubsections.length} of {subsections?.length ?? 0}
            </span>
          </div>

          {showSubsections ? (
            <ul className="flex flex-col gap-3">
              {filteredSubsections.length === 0 ? (
                <li>
                  <div
                    className="rounded-2xl border p-4 text-xs italic text-[var(--text-muted)]"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-raised)',
                    }}
                  >
                    No subsections match the selected focus filter.
                  </div>
                </li>
              ) : (
                filteredSubsections.map((subsection) => {
                  const chips = dedupeChips([
                    ...buildBaseChips(subsection),
                    ...buildHighlightChips(subsection),
                  ])

                  return (
                    <li key={subsection.id}>
                      <button
                        type="button"
                        className="flex w-full flex-col gap-3 rounded-2xl border p-4 text-left transition-colors"
                        style={{
                          borderColor: 'var(--lines-subtle)',
                          background: 'var(--surfaces-raised)',
                        }}
                        onClick={() => onSelectSubsection?.(sectionName, subsection)}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="flex flex-col gap-2">
                            <p className="text-sm font-semibold text-[var(--text-primary)]">
                              {subsection.name}
                            </p>
                            {subsection.synopsis ? (
                              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                                {subsection.synopsis}
                              </p>
                            ) : (
                              <p className="text-xs italic text-[var(--text-muted)]">
                                Synopsis not provided for this subsection.
                              </p>
                            )}
                          </div>
                          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                            View details →
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]">
                          {chips.map((chip) => renderChip(chip))}
                        </div>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          ) : null}
        </section>
      ) : null}
    </article>
  )
}
