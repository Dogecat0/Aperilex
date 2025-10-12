/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import type {
  ParsedSubsection,
  RiskSeverity,
  SubsectionSchemaData,
} from '@/lib/types/analysisSchemas'
import { BulletList, DetailGroup, InfoStack, MetricPill, SubtleTag } from './shared'

export function renderRiskDetail(analysis: ParsedSubsection) {
  switch (analysis.schemaType) {
    case 'RiskFactor':
      return <RiskFactorDetail data={analysis.data} />
    case 'IndustryRisk':
      return <IndustryRiskDetail data={analysis.data} />
    case 'RegulatoryRisk':
      return <RegulatoryRiskDetail data={analysis.data} />
    case 'FinancialRisk':
      return <FinancialRiskDetail data={analysis.data} />
    case 'OperationalRisk':
      return <OperationalRiskDetail data={analysis.data} />
    case 'ESGRisk':
      return <EsgRiskDetail data={analysis.data} />
    case 'RiskFactorsAnalysisSection':
      return <RiskFactorsAnalysisSectionDetail data={analysis.data} />
    default:
      return null
  }
}

function RiskFactorDetail({ data }: { data: SubsectionSchemaData<'RiskFactor'> }) {
  const tokens = useThemeTokens()
  const severityTone = toneForSeverity(data.severity)

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
        <div className="flex flex-wrap items-center gap-3">
          <MetricPill label="Severity" tone={severityTone}>
            {data.severity}
          </MetricPill>
          <SubtleTag>{data.category}</SubtleTag>
          {data.probability ? <SubtleTag>Probability · {data.probability}</SubtleTag> : null}
          {data.timeline ? <SubtleTag>Timeline · {data.timeline}</SubtleTag> : null}
        </div>
        <p className="text-sm leading-relaxed text-[var(--text-primary)]">{data.description}</p>
      </div>

      <DetailGroup title="Risk profile">
        <InfoStack
          items={[
            { label: 'Potential impact', value: data.potential_impact },
            {
              label: 'Mitigation measures',
              value: data.mitigation_measures ? (
                <ul className="list-disc pl-5 text-sm text-[var(--text-secondary)]">
                  {data.mitigation_measures.map((measure) => (
                    <li key={measure}>{measure}</li>
                  ))}
                </ul>
              ) : (
                'No mitigation captured'
              ),
            },
          ]}
        />
      </DetailGroup>
    </div>
  )
}

function IndustryRiskDetail({ data }: { data: SubsectionSchemaData<'IndustryRisk'> }) {
  return (
    <DetailGroup title="Industry risk outlook" description={data.industry_trends}>
      <BulletList title="Competitive pressures" items={data.competitive_pressures} />
      <InfoStack
        items={[
          { label: 'Market volatility', value: data.market_volatility ?? 'Not captured' },
          {
            label: 'Disruption threats',
            value: data.disruption_threats ? data.disruption_threats.join(', ') : 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function RegulatoryRiskDetail({ data }: { data: SubsectionSchemaData<'RegulatoryRisk'> }) {
  return (
    <DetailGroup title="Regulatory exposure" description={data.regulatory_environment}>
      <BulletList title="Compliance requirements" items={data.compliance_requirements} />
      <InfoStack
        items={[
          { label: 'Regulatory changes', value: data.regulatory_changes ?? 'Not captured' },
          { label: 'Enforcement risks', value: data.enforcement_risks ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function FinancialRiskDetail({ data }: { data: SubsectionSchemaData<'FinancialRisk'> }) {
  return (
    <DetailGroup title="Financial risk summary">
      <InfoStack
        columns={2}
        items={[
          { label: 'Credit risk', value: data.credit_risk ?? 'Not captured' },
          { label: 'Liquidity risk', value: data.liquidity_risk ?? 'Not captured' },
          { label: 'Market risk', value: data.market_risk ?? 'Not captured' },
          { label: 'Interest rate risk', value: data.interest_rate_risk ?? 'Not captured' },
          { label: 'Currency risk', value: data.currency_risk ?? 'Not captured' },
        ]}
      />
    </DetailGroup>
  )
}

function OperationalRiskDetail({ data }: { data: SubsectionSchemaData<'OperationalRisk'> }) {
  return (
    <DetailGroup title="Operational risk summary">
      <InfoStack
        columns={2}
        items={[
          {
            label: 'Key personnel dependence',
            value: data.key_personnel_dependence ?? 'Not captured',
          },
          {
            label: 'Supply chain disruption',
            value: data.supply_chain_disruption ?? 'Not captured',
          },
          {
            label: 'Technology failures',
            value: data.technology_failures ?? 'Not captured',
          },
          { label: 'Quality control', value: data.quality_control ?? 'Not captured' },
          {
            label: 'Capacity constraints',
            value: data.capacity_constraints ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function EsgRiskDetail({ data }: { data: SubsectionSchemaData<'ESGRisk'> }) {
  return (
    <DetailGroup title="ESG exposure overview">
      <BulletList title="Environmental risks" items={data.environmental_risks ?? undefined} />
      <InfoStack
        items={[
          { label: 'Social responsibility', value: data.social_responsibility ?? 'Not captured' },
          {
            label: 'Governance concerns',
            value: data.governance_concerns ? data.governance_concerns.join(', ') : 'Not captured',
          },
          {
            label: 'Sustainability challenges',
            value: data.sustainability_challenges ?? 'Not captured',
          },
        ]}
      />
    </DetailGroup>
  )
}

function RiskFactorsAnalysisSectionDetail({
  data,
}: {
  data: SubsectionSchemaData<'RiskFactorsAnalysisSection'>
}) {
  return (
    <div className="flex flex-col gap-4">
      <DetailGroup title="Executive summary" description={data.executive_summary}>
        <InfoStack
          items={[
            { label: 'Overall assessment', value: data.overall_risk_assessment },
            {
              label: 'Risk management framework',
              value: data.risk_management_framework ?? 'Not captured',
            },
          ]}
        />
      </DetailGroup>
      <SectionCollection title="Individual risk factors">
        {data.risk_factors.map((risk) => (
          <RiskFactorDetail key={risk.risk_name} data={risk} />
        ))}
      </SectionCollection>
      <SectionCollection title="Industry risks">
        <IndustryRiskDetail data={data.industry_risks} />
      </SectionCollection>
      <SectionCollection title="Regulatory risks">
        <RegulatoryRiskDetail data={data.regulatory_risks} />
      </SectionCollection>
      <SectionCollection title="Financial risks">
        <FinancialRiskDetail data={data.financial_risks} />
      </SectionCollection>
      <SectionCollection title="Operational risks">
        <OperationalRiskDetail data={data.operational_risks} />
      </SectionCollection>
      {data.esg_risks ? (
        <SectionCollection title="ESG risks">
          <EsgRiskDetail data={data.esg_risks} />
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

function toneForSeverity(severity: RiskSeverity) {
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
