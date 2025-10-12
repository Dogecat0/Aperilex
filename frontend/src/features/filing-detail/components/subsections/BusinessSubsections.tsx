/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import type { ParsedSubsection, SubsectionSchemaData } from '@/lib/types/analysisSchemas'
import { useThemeTokens } from '@/components/ThemeProvider'
import { DetailGroup, InfoStack, MetricPill, SubtleTag } from './shared'

export function renderBusinessDetail(analysis: ParsedSubsection) {
  switch (analysis.schemaType) {
    case 'OperationalOverview':
      return <OperationalOverviewDetail data={analysis.data} />
    case 'KeyProduct':
      return <KeyProductDetail data={analysis.data} />
    case 'CompetitiveAdvantage':
      return <CompetitiveAdvantageDetail data={analysis.data} />
    case 'StrategicInitiative':
      return <StrategicInitiativeDetail data={analysis.data} />
    case 'SupplyChain':
      return <SupplyChainDetail data={analysis.data} />
    case 'Partnership':
      return <PartnershipDetail data={analysis.data} />
    case 'BusinessSegmentAnalysis':
      return <BusinessSegmentAnalysisDetail data={analysis.data} />
    case 'GeographicSegmentAnalysis':
      return <GeographicSegmentAnalysisDetail data={analysis.data} />
    case 'BusinessAnalysisSection':
      return <BusinessAnalysisSectionDetail data={analysis.data} />
    default:
      return null
  }
}

function OperationalOverviewDetail({
  data,
}: {
  data: SubsectionSchemaData<'OperationalOverview'>
}) {
  const tokens = useThemeTokens()

  return (
    <div className="flex flex-col gap-4">
      <div
        className="flex flex-col gap-3 rounded-3xl border p-5"
        style={{
          borderColor: 'var(--lines-subtle)',
          background: tokens.surfaces.raised,
          boxShadow: tokens.shadows.medium,
        }}
      >
        <p className="text-sm leading-relaxed text-[var(--text-primary)]">{data.description}</p>
        <div className="flex flex-wrap gap-2">
          <MetricPill label="Industry" tone="neutral">
            {data.industry_classification}
          </MetricPill>
          {data.target_customers ? (
            <MetricPill label="Target customers" tone="notice">
              {data.target_customers}
            </MetricPill>
          ) : null}
          {data.business_model ? (
            <MetricPill label="Business model" tone="neutral">
              {data.business_model}
            </MetricPill>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {data.primary_markets.map((market) => (
            <SubtleTag key={market}>{market}</SubtleTag>
          ))}
        </div>
      </div>

      <DetailGroup title="Operational overview details">
        <InfoStack
          columns={2}
          items={[
            { label: 'Target customers', value: data.target_customers ?? 'Not captured' },
            { label: 'Business model', value: data.business_model ?? 'Not captured' },
            {
              label: 'Primary markets',
              value: (
                <div className="flex flex-wrap gap-2">
                  {data.primary_markets.map((market) => (
                    <SubtleTag key={market}>{market}</SubtleTag>
                  ))}
                </div>
              ),
            },
          ]}
        />
      </DetailGroup>
    </div>
  )
}

function KeyProductDetail({ data }: { data: SubsectionSchemaData<'KeyProduct'> }) {
  return (
    <DetailGroup title={data.name} description={data.description}>
      <InfoStack items={[{ label: 'Significance', value: data.significance ?? 'Not captured' }]} />
    </DetailGroup>
  )
}

function CompetitiveAdvantageDetail({
  data,
}: {
  data: SubsectionSchemaData<'CompetitiveAdvantage'>
}) {
  return (
    <DetailGroup title={data.advantage} description={data.description}>
      <InfoStack
        items={[
          {
            label: 'Key competitors',
            value: data.competitors ? (
              <ul className="list-disc pl-5 text-sm text-[var(--text-secondary)]">
                {data.competitors.map((competitor) => (
                  <li key={competitor}>{competitor}</li>
                ))}
              </ul>
            ) : (
              'No specific competitors noted'
            ),
          },
          {
            label: 'Sustainability',
            value: data.sustainability ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function StrategicInitiativeDetail({
  data,
}: {
  data: SubsectionSchemaData<'StrategicInitiative'>
}) {
  return (
    <DetailGroup title={data.name} description={data.description}>
      <InfoStack
        items={[
          { label: 'Impact', value: data.impact },
          { label: 'Timeframe', value: data.timeframe ?? 'Not captured' },
          { label: 'Resource allocation', value: data.resource_allocation ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function SupplyChainDetail({ data }: { data: SubsectionSchemaData<'SupplyChain'> }) {
  return (
    <DetailGroup title="Supply chain insights" description={data.description}>
      <InfoStack
        items={[
          {
            label: 'Key suppliers',
            value: data.key_suppliers ? data.key_suppliers.join(', ') : 'Not captured',
          },
          { label: 'Sourcing strategy', value: data.sourcing_strategy ?? 'Not captured' },
          { label: 'Risks', value: data.risks ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function PartnershipDetail({ data }: { data: SubsectionSchemaData<'Partnership'> }) {
  return (
    <DetailGroup title={data.name} description={data.description}>
      <InfoStack
        items={[
          { label: 'Partnership type', value: data.partnership_type },
          { label: 'Strategic value', value: data.strategic_value ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function BusinessSegmentAnalysisDetail({
  data,
}: {
  data: SubsectionSchemaData<'BusinessSegmentAnalysis'>
}) {
  return (
    <DetailGroup title={`${data.name} · ${data.segment_type}`} description={data.description}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Strategic importance', value: data.strategic_importance ?? 'Not captured' },
          { label: 'Market position', value: data.market_position ?? 'Not captured' },
          { label: 'Growth outlook', value: data.growth_outlook ?? 'Not captured' },
          {
            label: 'Key competitors',
            value: data.key_competitors ? data.key_competitors.join(', ') : 'Not captured',
          },
          { label: 'Relative size', value: data.relative_size ?? 'Not captured' },
          { label: 'Market trends', value: data.market_trends ?? 'Not captured' },
          {
            label: 'Product differentiation',
            value: data.product_differentiation ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function GeographicSegmentAnalysisDetail({
  data,
}: {
  data: SubsectionSchemaData<'GeographicSegmentAnalysis'>
}) {
  return (
    <DetailGroup title={`${data.name} · ${data.region}`} description={data.description}>
      <InfoStack
        columns={2}
        items={[
          { label: 'Strategic importance', value: data.strategic_importance ?? 'Not captured' },
          { label: 'Market position', value: data.market_position ?? 'Not captured' },
          { label: 'Growth outlook', value: data.growth_outlook ?? 'Not captured' },
          {
            label: 'Key competitors',
            value: data.key_competitors ? data.key_competitors.join(', ') : 'Not captured',
          },
          { label: 'Relative size', value: data.relative_size ?? 'Not captured' },
          {
            label: 'Market characteristics',
            value: data.market_characteristics ?? 'Not captured',
          },
          {
            label: 'Regulatory environment',
            value: data.regulatory_environment ?? 'Not captured',
          },
          { label: 'Expansion strategy', value: data.expansion_strategy ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function BusinessAnalysisSectionDetail({
  data,
}: {
  data: SubsectionSchemaData<'BusinessAnalysisSection'>
}) {
  return (
    <div className="flex flex-col gap-4">
      <OperationalOverviewDetail data={data.operational_overview} />
      <SectionCollection
        title="Key products"
        description="Products and services called out by the analysis provider."
      >
        {data.key_products.map((product) => (
          <KeyProductDetail key={product.name} data={product} />
        ))}
      </SectionCollection>
      <SectionCollection
        title="Competitive advantages"
        description="Defensible differentiators highlighted for this filing."
      >
        {data.competitive_advantages.map((advantage) => (
          <CompetitiveAdvantageDetail key={advantage.advantage} data={advantage} />
        ))}
      </SectionCollection>
      <SectionCollection
        title="Strategic initiatives"
        description="Initiatives underway with impact, timeframe, and resource notes."
      >
        {data.strategic_initiatives.map((initiative) => (
          <StrategicInitiativeDetail key={initiative.name} data={initiative} />
        ))}
      </SectionCollection>
      <SectionCollection title="Business segments">
        {data.business_segments.map((segment) => (
          <BusinessSegmentAnalysisDetail key={segment.name} data={segment} />
        ))}
      </SectionCollection>
      <SectionCollection title="Geographic segments">
        {data.geographic_segments.map((segment) => (
          <GeographicSegmentAnalysisDetail key={segment.name} data={segment} />
        ))}
      </SectionCollection>
      {data.supply_chain ? <SupplyChainDetail data={data.supply_chain} /> : null}
      {data.partnerships && data.partnerships.length > 0 ? (
        <SectionCollection title="Partnerships">
          {data.partnerships.map((partnership) => (
            <PartnershipDetail key={partnership.name} data={partnership} />
          ))}
        </SectionCollection>
      ) : null}
    </div>
  )
}

function SectionCollection({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3">
      <header className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {title}
        </p>
        {description ? (
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{description}</p>
        ) : null}
      </header>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  )
}
