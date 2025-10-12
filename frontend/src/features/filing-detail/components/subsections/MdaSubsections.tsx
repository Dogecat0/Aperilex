/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import type {
  OutlookSentiment,
  ParsedSubsection,
  SubsectionSchemaData,
} from '@/lib/types/analysisSchemas'
import { BulletList, DetailGroup, InfoStack, MetricPill, SubtleTag } from './shared'

export function renderMdaDetail(analysis: ParsedSubsection) {
  switch (analysis.schemaType) {
    case 'FinancialMetric':
      return <FinancialMetricDetail data={analysis.data} />
    case 'RevenueAnalysis':
      return <RevenueAnalysisDetail data={analysis.data} />
    case 'ProfitabilityAnalysis':
      return <ProfitabilityAnalysisDetail data={analysis.data} />
    case 'LiquidityAnalysis':
      return <LiquidityAnalysisDetail data={analysis.data} />
    case 'OperationalHighlights':
      return <OperationalHighlightDetail data={analysis.data} />
    case 'MarketCondition':
      return <MarketConditionDetail data={analysis.data} />
    case 'ForwardLookingStatement':
      return <ForwardLookingStatementDetail data={analysis.data} />
    case 'CriticalAccounting':
      return <CriticalAccountingDetail data={analysis.data} />
    case 'MDAAnalysisSection':
      return <MdaAnalysisSectionDetail data={analysis.data} />
    default:
      return null
  }
}

function FinancialMetricDetail({ data }: { data: SubsectionSchemaData<'FinancialMetric'> }) {
  const tokens = useThemeTokens()
  const tone = directionTone(data.direction)

  return (
    <div
      className="flex flex-col gap-3 rounded-3xl border p-5"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: tokens.surfaces.raised,
        boxShadow: tokens.shadows.soft,
      }}
    >
      <div className="flex flex-wrap items-center gap-3">
        <h4 className="text-base font-semibold text-[var(--text-primary)]">{data.metric_name}</h4>
        <MetricPill label="Direction" tone={tone}>
          {data.direction}
        </MetricPill>
        {data.percentage_change ? <SubtleTag>Δ {data.percentage_change}</SubtleTag> : null}
      </div>
      <InfoStack
        columns={2}
        items={[
          { label: 'Current value', value: data.current_value ?? 'Not captured' },
          { label: 'Previous value', value: data.previous_value ?? 'Not captured' },
          { label: 'Explanation', value: data.explanation },
          { label: 'Significance', value: data.significance },
        ]}
      />
    </div>
  )
}

function RevenueAnalysisDetail({ data }: { data: SubsectionSchemaData<'RevenueAnalysis'> }) {
  return (
    <DetailGroup title="Revenue analysis" description={data.total_revenue_performance}>
      <BulletList title="Key revenue drivers" items={data.revenue_drivers} />
      <BulletList title="Headwinds" items={data.revenue_headwinds ?? undefined} />
      <BulletList title="Segment highlights" items={data.segment_performance ?? undefined} />
      <BulletList title="Geographic performance" items={data.geographic_performance ?? undefined} />
      <InfoStack
        items={[
          {
            label: 'Recurring vs one-time mix',
            value: data.recurring_vs_onetime ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function ProfitabilityAnalysisDetail({
  data,
}: {
  data: SubsectionSchemaData<'ProfitabilityAnalysis'>
}) {
  return (
    <DetailGroup title="Profitability analysis">
      <InfoStack
        items={[
          { label: 'Gross margin', value: data.gross_margin_analysis ?? 'Not captured' },
          { label: 'Operating margin', value: data.operating_margin_analysis ?? 'Not captured' },
          { label: 'Net margin', value: data.net_margin_analysis ?? 'Not captured' },
        ]}
      />
      <BulletList title="Cost structure changes" items={data.cost_structure_changes ?? undefined} />
      <BulletList
        title="Efficiency improvements"
        items={data.efficiency_improvements ?? undefined}
      />
    </DetailGroup>
  )
}

function LiquidityAnalysisDetail({ data }: { data: SubsectionSchemaData<'LiquidityAnalysis'> }) {
  return (
    <DetailGroup title="Liquidity analysis" description={data.cash_flow_analysis}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Cash position', value: data.cash_position ?? 'Not captured' },
          { label: 'Working capital', value: data.working_capital ?? 'Not captured' },
          { label: 'Debt analysis', value: data.debt_analysis ?? 'Not captured' },
          { label: 'Credit facilities', value: data.credit_facilities ?? 'Not captured' },
          { label: 'Capital allocation', value: data.capital_allocation ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function OperationalHighlightDetail({
  data,
}: {
  data: SubsectionSchemaData<'OperationalHighlights'>
}) {
  return (
    <DetailGroup title={data.achievement} description={data.impact}>
      <InfoStack
        items={[
          {
            label: 'Strategic significance',
            value: data.strategic_significance ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function MarketConditionDetail({ data }: { data: SubsectionSchemaData<'MarketCondition'> }) {
  return (
    <DetailGroup title="Market conditions" description={data.market_description}>
      <InfoStack
        items={[
          { label: 'Business impact', value: data.impact_on_business },
          {
            label: 'Competitive dynamics',
            value: data.competitive_dynamics ?? 'Not captured',
          },
        ]}
      />
      <BulletList title="Opportunities & threats" items={data.opportunity_threats ?? undefined} />
    </DetailGroup>
  )
}

function ForwardLookingStatementDetail({
  data,
}: {
  data: SubsectionSchemaData<'ForwardLookingStatement'>
}) {
  return (
    <DetailGroup title={data.statement}>
      <InfoStack
        items={[
          { label: 'Metric area', value: data.metric_area },
          { label: 'Timeframe', value: data.timeframe ?? 'Not captured' },
        ]}
      />
      <BulletList title="Assumptions" items={data.assumptions ?? undefined} />
      <BulletList title="Risks to guidance" items={data.risks_to_guidance ?? undefined} />
    </DetailGroup>
  )
}

function CriticalAccountingDetail({ data }: { data: SubsectionSchemaData<'CriticalAccounting'> }) {
  return (
    <DetailGroup title={data.policy_name} description={data.description}>
      <BulletList title="Judgment areas" items={data.judgment_areas} />
      <InfoStack
        items={[{ label: 'Impact on results', value: data.impact_on_results ?? 'Not captured' }]}
      />
    </DetailGroup>
  )
}

function MdaAnalysisSectionDetail({ data }: { data: SubsectionSchemaData<'MDAAnalysisSection'> }) {
  return (
    <div className="flex flex-col gap-4">
      <DetailGroup title="Executive overview" description={data.executive_overview}>
        <InfoStack
          items={[
            { label: 'Outlook summary', value: data.outlook_summary },
            {
              label: 'Outlook sentiment',
              value: (
                <SentimentPill sentiment={data.outlook_sentiment}>
                  {data.outlook_sentiment}
                </SentimentPill>
              ),
            },
            {
              label: 'Management priorities',
              value: data.management_priorities
                ? data.management_priorities.join(', ')
                : 'Not captured',
            },
          ]}
        />
      </DetailGroup>
      <SectionCollection title="Key financial metrics">
        {data.key_financial_metrics.map((metric) => (
          <FinancialMetricDetail key={metric.metric_name} data={metric} />
        ))}
      </SectionCollection>
      <SectionCollection title="Revenue analysis">
        <RevenueAnalysisDetail data={data.revenue_analysis} />
      </SectionCollection>
      <SectionCollection title="Profitability analysis">
        <ProfitabilityAnalysisDetail data={data.profitability_analysis} />
      </SectionCollection>
      <SectionCollection title="Liquidity analysis">
        <LiquidityAnalysisDetail data={data.liquidity_analysis} />
      </SectionCollection>
      <SectionCollection title="Operational highlights">
        {data.operational_highlights.map((highlight) => (
          <OperationalHighlightDetail key={highlight.achievement} data={highlight} />
        ))}
      </SectionCollection>
      <SectionCollection title="Market conditions">
        {data.market_conditions.map((condition, index) => (
          <MarketConditionDetail
            key={`${condition.market_description}-${index}`}
            data={condition}
          />
        ))}
      </SectionCollection>
      {data.forward_looking_statements && data.forward_looking_statements.length > 0 ? (
        <SectionCollection title="Forward-looking statements">
          {data.forward_looking_statements.map((statement, index) => (
            <ForwardLookingStatementDetail
              key={`${statement.statement}-${index}`}
              data={statement}
            />
          ))}
        </SectionCollection>
      ) : null}
      {data.critical_accounting_policies && data.critical_accounting_policies.length > 0 ? (
        <SectionCollection title="Critical accounting policies">
          {data.critical_accounting_policies.map((policy) => (
            <CriticalAccountingDetail key={policy.policy_name} data={policy} />
          ))}
        </SectionCollection>
      ) : null}
    </div>
  )
}

function SectionCollection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {title}
      </h4>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  )
}

function SentimentPill({
  sentiment,
  children,
}: {
  sentiment: OutlookSentiment
  children: ReactNode
}) {
  const tone =
    sentiment === 'Positive' || sentiment === 'Optimistic'
      ? 'positive'
      : sentiment === 'Negative'
        ? 'negative'
        : sentiment === 'Cautious'
          ? 'notice'
          : 'neutral'

  return (
    <MetricPill label="Sentiment" tone={tone}>
      {children}
    </MetricPill>
  )
}

function directionTone(direction: SubsectionSchemaData<'FinancialMetric'>['direction']) {
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
