/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import { DetailGroup, InfoStack, BulletList } from './shared'
import type { ParsedSubsection, SubsectionSchemaData } from '@/lib/types/analysisSchemas'

export function renderFinancialDetail(analysis: ParsedSubsection) {
  switch (analysis.schemaType) {
    case 'FinancialRatio':
      return <FinancialRatioDetail data={analysis.data} />
    case 'AssetComposition':
      return <AssetCompositionDetail data={analysis.data} />
    case 'LiabilityStructure':
      return <LiabilityStructureDetail data={analysis.data} />
    case 'EquityAnalysis':
      return <EquityAnalysisDetail data={analysis.data} />
    case 'RevenueSegment':
      return <RevenueSegmentDetail data={analysis.data} />
    case 'ExpenseCategory':
      return <ExpenseCategoryDetail data={analysis.data} />
    case 'ProfitabilityMetric':
      return <ProfitabilityMetricDetail data={analysis.data} />
    case 'OperatingCashFlow':
      return <OperatingCashFlowDetail data={analysis.data} />
    case 'InvestingCashFlow':
      return <InvestingCashFlowDetail data={analysis.data} />
    case 'FinancingCashFlow':
      return <FinancingCashFlowDetail data={analysis.data} />
    case 'CashFlowRatio':
      return <CashFlowRatioDetail data={analysis.data} />
    case 'BalanceSheetAnalysisSection':
      return <BalanceSheetAnalysisSectionDetail data={analysis.data} />
    case 'IncomeStatementAnalysisSection':
      return <IncomeStatementAnalysisSectionDetail data={analysis.data} />
    case 'CashFlowAnalysisSection':
      return <CashFlowAnalysisSectionDetail data={analysis.data} />
    default:
      return null
  }
}

function FinancialRatioDetail({ data }: { data: SubsectionSchemaData<'FinancialRatio'> }) {
  return (
    <DetailGroup title={data.ratio_name}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Current value', value: formatNumber(data.current_value) },
          { label: 'Previous value', value: formatNumber(data.previous_value) },
          { label: 'Industry benchmark', value: formatNumber(data.industry_benchmark) },
          { label: 'Interpretation', value: data.interpretation },
        ]}
      />
    </DetailGroup>
  )
}

function AssetCompositionDetail({ data }: { data: SubsectionSchemaData<'AssetComposition'> }) {
  return (
    <DetailGroup title="Asset composition">
      <InfoStack
        columns={2}
        items={[
          { label: 'Current assets %', value: formatPercentage(data.current_assets_percentage) },
          {
            label: 'Non-current assets %',
            value: formatPercentage(data.non_current_assets_percentage),
          },
          {
            label: 'Asset quality',
            value: data.asset_quality_assessment,
          },
        ]}
      />
      <BulletList title="Key asset categories" items={data.key_asset_categories} />
    </DetailGroup>
  )
}

function LiabilityStructureDetail({ data }: { data: SubsectionSchemaData<'LiabilityStructure'> }) {
  return (
    <DetailGroup title="Liability structure">
      <InfoStack
        columns={2}
        items={[
          {
            label: 'Current liabilities %',
            value: formatPercentage(data.current_liabilities_percentage),
          },
          {
            label: 'Long-term debt %',
            value: formatPercentage(data.long_term_debt_percentage),
          },
          { label: 'Debt maturity profile', value: data.debt_maturity_profile },
        ]}
      />
      <BulletList title="Liability concerns" items={data.liability_concerns} />
    </DetailGroup>
  )
}

function EquityAnalysisDetail({ data }: { data: SubsectionSchemaData<'EquityAnalysis'> }) {
  return (
    <DetailGroup title="Equity analysis">
      <InfoStack
        items={[
          { label: 'Total equity change', value: data.total_equity_change },
          { label: 'Retained earnings trend', value: data.retained_earnings_trend },
          { label: 'Share capital changes', value: data.share_capital_changes },
          { label: 'Equity quality assessment', value: data.equity_quality_assessment },
        ]}
      />
    </DetailGroup>
  )
}

function RevenueSegmentDetail({ data }: { data: SubsectionSchemaData<'RevenueSegment'> }) {
  return (
    <DetailGroup title={data.segment_name} description={data.performance_commentary}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Revenue amount', value: data.revenue_amount ?? 'Not captured' },
          { label: 'Growth rate', value: data.growth_rate ?? 'Not captured' },
          { label: 'Share of total', value: formatPercentage(data.percentage_of_total) },
        ]}
      />
    </DetailGroup>
  )
}

function ExpenseCategoryDetail({ data }: { data: SubsectionSchemaData<'ExpenseCategory'> }) {
  return (
    <DetailGroup title={data.category_name} description={data.efficiency_assessment}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Amount', value: data.amount ?? 'Not captured' },
          { label: 'Percent of revenue', value: formatPercentage(data.percentage_of_revenue) },
          { label: 'YoY change', value: data.year_over_year_change ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function ProfitabilityMetricDetail({
  data,
}: {
  data: SubsectionSchemaData<'ProfitabilityMetric'>
}) {
  return (
    <DetailGroup title={data.metric_name} description={data.trend_analysis}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Current value', value: data.current_value ?? 'Not captured' },
          { label: 'Previous value', value: data.previous_value ?? 'Not captured' },
          { label: 'Margin %', value: formatPercentage(data.margin_percentage) },
        ]}
      />
    </DetailGroup>
  )
}

function OperatingCashFlowDetail({ data }: { data: SubsectionSchemaData<'OperatingCashFlow'> }) {
  return (
    <DetailGroup title="Operating cash flow" description={data.working_capital_impact}>
      <InfoStack
        items={[
          {
            label: 'Net cash from operations',
            value: data.net_cash_from_operations ?? 'Not captured',
          },
          { label: 'Cash conversion ratio', value: formatNumber(data.cash_conversion_ratio) },
          { label: 'Quality assessment', value: data.quality_assessment },
        ]}
      />
    </DetailGroup>
  )
}

function InvestingCashFlowDetail({ data }: { data: SubsectionSchemaData<'InvestingCashFlow'> }) {
  return (
    <DetailGroup title="Investing cash flow" description={data.investment_strategy_commentary}>
      <InfoStack
        items={[
          {
            label: 'Net cash from investing',
            value: data.net_cash_from_investing ?? 'Not captured',
          },
          { label: 'Capital expenditures', value: data.capital_expenditures ?? 'Not captured' },
          { label: 'Asset acquisitions', value: data.asset_acquisitions ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function FinancingCashFlowDetail({ data }: { data: SubsectionSchemaData<'FinancingCashFlow'> }) {
  return (
    <DetailGroup title="Financing cash flow" description={data.financing_strategy_commentary}>
      <InfoStack
        items={[
          {
            label: 'Net cash from financing',
            value: data.net_cash_from_financing ?? 'Not captured',
          },
          { label: 'Debt changes', value: data.debt_changes ?? 'Not captured' },
          { label: 'Dividend payments', value: data.dividend_payments ?? 'Not captured' },
          { label: 'Share repurchases', value: data.share_repurchases ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function CashFlowRatioDetail({ data }: { data: SubsectionSchemaData<'CashFlowRatio'> }) {
  return (
    <DetailGroup title={data.ratio_name}>
      <InfoStack
        items={[
          { label: 'Current value', value: formatNumber(data.current_value) },
          { label: 'Previous value', value: formatNumber(data.previous_value) },
          { label: 'Interpretation', value: data.interpretation },
        ]}
      />
    </DetailGroup>
  )
}

function BalanceSheetAnalysisSectionDetail({
  data,
}: {
  data: SubsectionSchemaData<'BalanceSheetAnalysisSection'>
}) {
  return (
    <div className="flex flex-col gap-4">
      <DetailGroup title={data.section_summary}>
        <InfoStack
          columns={2}
          items={[
            { label: 'Period covered', value: data.period_covered },
            { label: 'Total assets', value: data.total_assets ?? 'Not captured' },
            { label: 'Total liabilities', value: data.total_liabilities ?? 'Not captured' },
            { label: 'Total equity', value: data.total_equity ?? 'Not captured' },
            { label: 'Liquidity position', value: data.liquidity_position },
            { label: 'Debt level', value: data.debt_level },
            { label: 'Overall trend', value: data.overall_trend },
          ]}
        />
      </DetailGroup>
      <SectionCollection title="Asset composition">
        <AssetCompositionDetail data={data.asset_composition} />
      </SectionCollection>
      <SectionCollection title="Liability structure">
        <LiabilityStructureDetail data={data.liability_structure} />
      </SectionCollection>
      <SectionCollection title="Equity analysis">
        <EquityAnalysisDetail data={data.equity_analysis} />
      </SectionCollection>
      <SectionCollection title="Key ratios">
        {data.key_ratios.map((ratio) => (
          <FinancialRatioDetail key={ratio.ratio_name} data={ratio} />
        ))}
      </SectionCollection>
      <DetailGroup title="Insights">
        <BulletList title="Strengths" items={data.strengths} />
        <BulletList title="Concerns" items={data.concerns} />
        <BulletList title="Year-over-year changes" items={data.year_over_year_changes} />
        <BulletList title="Notable items" items={data.notable_items} />
        <InfoStack
          items={[
            { label: 'Management commentary', value: data.management_commentary ?? 'Not captured' },
          ]}
        />
      </DetailGroup>
    </div>
  )
}

function IncomeStatementAnalysisSectionDetail({
  data,
}: {
  data: SubsectionSchemaData<'IncomeStatementAnalysisSection'>
}) {
  return (
    <div className="flex flex-col gap-4">
      <DetailGroup title={data.section_summary}>
        <InfoStack
          columns={2}
          items={[
            { label: 'Period covered', value: data.period_covered },
            { label: 'Total revenue', value: data.total_revenue ?? 'Not captured' },
            { label: 'Net income', value: data.net_income ?? 'Not captured' },
            { label: 'Earnings per share', value: data.earnings_per_share ?? 'Not captured' },
            { label: 'Revenue trend', value: data.revenue_trend },
            { label: 'Profitability level', value: data.profitability_level },
            { label: 'Expense control', value: data.expense_control },
            { label: 'Revenue growth', value: data.revenue_growth_rate ?? 'Not captured' },
            {
              label: 'Operating income growth',
              value: data.operating_income_growth ?? 'Not captured',
            },
            { label: 'Net income growth', value: data.net_income_growth ?? 'Not captured' },
            { label: 'Gross margin', value: formatPercentage(data.gross_margin) },
            { label: 'Operating margin', value: formatPercentage(data.operating_margin) },
            { label: 'Net margin', value: formatPercentage(data.net_margin) },
          ]}
        />
      </DetailGroup>
      <SectionCollection title="Revenue segments">
        {data.revenue_segments.map((segment) => (
          <RevenueSegmentDetail key={segment.segment_name} data={segment} />
        ))}
      </SectionCollection>
      <SectionCollection title="Expense categories">
        {data.expense_categories.map((category) => (
          <ExpenseCategoryDetail key={category.category_name} data={category} />
        ))}
      </SectionCollection>
      <SectionCollection title="Profitability metrics">
        {data.profitability_metrics.map((metric) => (
          <ProfitabilityMetricDetail key={metric.metric_name} data={metric} />
        ))}
      </SectionCollection>
      <DetailGroup title="Insights">
        <BulletList title="Performance highlights" items={data.performance_highlights} />
        <BulletList title="Areas of concern" items={data.areas_of_concern} />
        <BulletList title="Competitive advantages" items={data.competitive_advantages} />
        <BulletList title="Seasonal factors" items={data.seasonal_factors ?? undefined} />
        <BulletList title="One-time items" items={data.one_time_items ?? undefined} />
        <InfoStack
          items={[
            { label: 'Management commentary', value: data.management_commentary ?? 'Not captured' },
          ]}
        />
      </DetailGroup>
    </div>
  )
}

function CashFlowAnalysisSectionDetail({
  data,
}: {
  data: SubsectionSchemaData<'CashFlowAnalysisSection'>
}) {
  return (
    <div className="flex flex-col gap-4">
      <DetailGroup title={data.section_summary}>
        <InfoStack
          columns={2}
          items={[
            { label: 'Period covered', value: data.period_covered },
            { label: 'Beginning cash', value: data.beginning_cash ?? 'Not captured' },
            { label: 'Ending cash', value: data.ending_cash ?? 'Not captured' },
            { label: 'Net change in cash', value: data.net_change_in_cash ?? 'Not captured' },
            { label: 'Cash flow trend', value: data.cash_flow_trend },
            { label: 'Cash position', value: data.cash_position },
            { label: 'Cash flow quality', value: data.cash_flow_quality },
            { label: 'Free cash flow', value: data.free_cash_flow ?? 'Not captured' },
            {
              label: 'Free cash flow yield',
              value: formatPercentage(data.free_cash_flow_yield),
            },
            {
              label: 'Free cash flow growth',
              value: data.free_cash_flow_growth ?? 'Not captured',
            },
            {
              label: 'Cash runway assessment',
              value: data.cash_runway_assessment,
            },
            {
              label: 'Debt service coverage',
              value: data.debt_service_coverage ?? 'Not captured',
            },
          ]}
        />
      </DetailGroup>
      <SectionCollection title="Operating cash flow">
        <OperatingCashFlowDetail data={data.operating_cash_flow} />
      </SectionCollection>
      <SectionCollection title="Investing cash flow">
        <InvestingCashFlowDetail data={data.investing_cash_flow} />
      </SectionCollection>
      <SectionCollection title="Financing cash flow">
        <FinancingCashFlowDetail data={data.financing_cash_flow} />
      </SectionCollection>
      <SectionCollection title="Cash flow ratios">
        {data.cash_flow_ratios.map((ratio) => (
          <CashFlowRatioDetail key={ratio.ratio_name} data={ratio} />
        ))}
      </SectionCollection>
      <DetailGroup title="Capital allocation priorities">
        <BulletList title="Priorities" items={data.capital_allocation_priorities} />
      </DetailGroup>
      <DetailGroup title="Insights">
        <BulletList title="Strengths" items={data.cash_flow_strengths} />
        <BulletList title="Concerns" items={data.cash_flow_concerns} />
        <BulletList title="Seasonal patterns" items={data.seasonal_patterns} />
        <InfoStack
          items={[
            { label: 'Management commentary', value: data.management_commentary ?? 'Not captured' },
          ]}
        />
      </DetailGroup>
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

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'Not captured'
  }

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercentage(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return 'Not captured'
  }

  return `${formatNumber(value)}%`
}
