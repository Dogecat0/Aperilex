import type { ReactNode } from 'react'
import type { ParsedSubsection } from '@/lib/types/analysisSchemas'
import { DetailGroup } from './shared'
import { renderBusinessDetail } from './BusinessSubsections'
import { renderRiskDetail } from './RiskSubsections'
import { renderMdaDetail } from './MdaSubsections'
import { renderFinancialDetail } from './FinancialSubsections'

interface SubsectionDetailContentProps {
  analysis: ParsedSubsection
}

export function SubsectionDetailContent({ analysis }: SubsectionDetailContentProps) {
  switch (analysis.schemaType) {
    case 'OperationalOverview':
    case 'KeyProduct':
    case 'CompetitiveAdvantage':
    case 'StrategicInitiative':
    case 'SupplyChain':
    case 'Partnership':
    case 'BusinessSegmentAnalysis':
    case 'GeographicSegmentAnalysis':
    case 'BusinessAnalysisSection':
      return renderBusinessDetail(analysis)
    case 'RiskFactor':
    case 'IndustryRisk':
    case 'RegulatoryRisk':
    case 'FinancialRisk':
    case 'OperationalRisk':
    case 'ESGRisk':
    case 'RiskFactorsAnalysisSection':
      return renderRiskDetail(analysis)
    case 'FinancialMetric':
    case 'RevenueAnalysis':
    case 'ProfitabilityAnalysis':
    case 'LiquidityAnalysis':
    case 'OperationalHighlights':
    case 'MarketCondition':
    case 'ForwardLookingStatement':
    case 'CriticalAccounting':
    case 'MDAAnalysisSection':
      return renderMdaDetail(analysis)
    case 'FinancialRatio':
    case 'AssetComposition':
    case 'LiabilityStructure':
    case 'EquityAnalysis':
    case 'RevenueSegment':
    case 'ExpenseCategory':
    case 'ProfitabilityMetric':
    case 'OperatingCashFlow':
    case 'InvestingCashFlow':
    case 'FinancingCashFlow':
    case 'CashFlowRatio':
    case 'BalanceSheetAnalysisSection':
    case 'IncomeStatementAnalysisSection':
    case 'CashFlowAnalysisSection':
      return renderFinancialDetail(analysis)
    default:
      return (
        <DetailGroup title="Structured details">
          <FallbackDetail payload={analysis.data} />
        </DetailGroup>
      )
  }
}

interface FallbackDetailProps {
  payload: unknown
}

function FallbackDetail({ payload }: FallbackDetailProps) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return (
      <p className="text-sm italic text-[var(--text-muted)]">
        Structured payload not available for this subsection.
      </p>
    )
  }

  const entries = Object.entries(payload as Record<string, unknown>)
  if (entries.length === 0) {
    return (
      <p className="text-sm italic text-[var(--text-muted)]">
        Structured payload returned an empty object.
      </p>
    )
  }

  return (
    <dl className="grid gap-3">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-1">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {key.replace(/[_-]+/g, ' ')}
          </dt>
          <dd className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {formatValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function formatValue(value: unknown, depth = 0): ReactNode {
  if (typeof value === 'string') {
    return value
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-xs italic text-[var(--text-muted)]">Empty list</span>
    }

    return (
      <ul className="list-disc pl-5">
        {value.map((entry, index) => (
          <li key={index}>{formatValue(entry, depth + 1)}</li>
        ))}
      </ul>
    )
  }

  if (!value || typeof value !== 'object' || depth > 1) {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }

  return (
    <dl className="grid gap-2 pl-3">
      {Object.entries(value as Record<string, unknown>).map(([nestedKey, nestedValue]) => (
        <div key={nestedKey} className="flex flex-col gap-1">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {nestedKey.replace(/[_-]+/g, ' ')}
          </dt>
          <dd className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {formatValue(nestedValue, depth + 1)}
          </dd>
        </div>
      ))}
    </dl>
  )
}
