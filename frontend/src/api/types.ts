// API Response Types - Generated from OpenAPI Schema

// Base Types
export interface PaginationMetadata {
  page: number
  page_size: number
  total_items: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
  next_page: number | null
  previous_page: number | null
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMetadata
  query_id?: string
  filters_applied?: string
}

// Company Types
export interface CompanyAddress {
  street?: string
  city?: string
  state?: string
  zipcode?: string
  country?: string
}

export interface CompanyResponse {
  company_id: string
  cik: string
  name: string
  ticker: string | null
  display_name: string
  industry: string | null
  sic_code: string | null
  sic_description: string | null
  fiscal_year_end: string | null
  business_address: CompanyAddress | null
  recent_analyses?: Array<{
    analysis_id: string
    analysis_template: AnalysisTemplate
    created_at: string
    confidence_score?: number
  }>
}

// Filing Types
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface FilingResponse {
  filing_id: string
  company_id: string
  accession_number: string
  filing_type: string
  filing_date: string
  processing_status: ProcessingStatus
  processing_error: string | null
  metadata: Record<string, string | number | boolean | null>
  analyses_count?: number
  latest_analysis_date?: string
}

// Analysis Types
export type AnalysisTemplate =
  | 'comprehensive'
  | 'financial_focused'
  | 'risk_focused'
  | 'business_focused'

// Analysis Result Types
export interface AnalysisSectionResult {
  section_name: string
  summary?: string
  key_points?: string[]
  sentiment?: 'positive' | 'negative' | 'neutral' | 'mixed'
  confidence?: number
}

export interface AnalysisFullResults {
  sections?: AnalysisSectionResult[]
  overall_sentiment?: 'positive' | 'negative' | 'neutral' | 'mixed'
  metadata?: Record<string, string | number | boolean | null>
}

export interface AnalysisResponse {
  analysis_id: string
  filing_id: string
  analysis_template: AnalysisTemplate
  created_by: string | null
  created_at: string
  confidence_score: number | null
  llm_provider: string | null
  llm_model: string | null
  processing_time_seconds: number | null

  // Summary data
  filing_summary?: string
  executive_summary?: string
  key_insights?: string[]
  risk_factors?: string[]
  opportunities?: string[]
  financial_highlights?: string[]
  sections_analyzed?: number

  // Full results (optional)
  full_results?: AnalysisFullResults
}

// Task Types
export type TaskStatus = 'pending' | 'started' | 'success' | 'failure' | 'completed'

export interface TaskResult {
  analysis?: AnalysisResponse
  filing?: FilingResponse
  error?: string
  metadata?: Record<string, string | number | boolean | null>
}

export interface TaskResponse {
  task_id: string
  status: TaskStatus
  result: TaskResult | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  progress_percent: number | null
  current_step: string | null
}

// Progressive Loading States
export type AnalysisProgressState =
  | 'idle'
  | 'initiating'
  | 'loading_filing'
  | 'analyzing_content'
  | 'completing'
  | 'completed'
  | 'error'
  | 'processing_background'

export interface AnalysisProgress {
  state: AnalysisProgressState
  message: string
  progress_percent?: number
  current_step?: string
  task_id?: string
}

// Template Types
export interface AnalysisTemplateConfig {
  name: AnalysisTemplate
  description: string
  sections: string[]
}

export interface TemplatesResponse {
  templates: AnalysisTemplateConfig[]
}

// Request Types
export interface AnalyzeFilingRequest {
  analysis_template?: AnalysisTemplate
  sections?: string[]
  force_reanalysis?: boolean
}

export interface ListAnalysesParams {
  page?: number
  page_size?: number
  company_cik?: string
  analysis_template?: AnalysisTemplate
  created_from?: string
  created_to?: string
  min_confidence_score?: number
}

// Health Types
export interface HealthStatusDetails {
  version?: string
  uptime?: number
  memory_usage?: number
  cpu_usage?: number
  [key: string]: string | number | boolean | undefined
}

export interface HealthStatus {
  status: string
  message?: string
  timestamp: string
  details?: HealthStatusDetails
}

export interface HealthResponse {
  status: string
  message?: string
  version?: string
  environment?: string
  timestamp: string
}

export interface DetailedHealthResponse {
  status: string
  timestamp: string
  version: string
  environment: string
  services: Record<string, HealthStatus>
  configuration: {
    redis_enabled: boolean
    celery_enabled: boolean
    debug: boolean
    redis_url_configured: boolean
    celery_broker_configured: boolean
  }
}

// Error Types
export interface APIError {
  detail: string
  status_code: number
  error_code?: string
}

export interface ValidationError {
  detail: Array<{
    loc: (string | number)[]
    msg: string
    type: string
  }>
}

// Filing Search Types
export interface FilingSearchResult {
  accession_number: string
  filing_type: string
  filing_date: string // ISO date string
  company_name: string
  cik: string
  ticker: string | null
  has_content: boolean
  sections_count: number
}

// ===== COMPREHENSIVE ANALYSIS TYPES =====

// Type-safe constants for business segment values
export const BusinessSegment = {
  TECHNOLOGY: 'Technology',
  FINANCIAL_SERVICES: 'Financial Services',
  HEALTHCARE: 'Healthcare',
  MANUFACTURING: 'Manufacturing',
  RETAIL: 'Retail',
  ENERGY: 'Energy',
  REAL_ESTATE: 'Real Estate',
  TELECOMMUNICATIONS: 'Telecommunications',
  TRANSPORTATION: 'Transportation',
  UTILITIES: 'Utilities',
  CONSUMER_GOODS: 'Consumer Goods',
  MEDIA: 'Media',
  EDUCATION: 'Education',
  GOVERNMENT: 'Government',
  NON_PROFIT: 'Non-Profit',
  OTHER: 'Other',
} as const

export type BusinessSegment = (typeof BusinessSegment)[keyof typeof BusinessSegment]

export const Region = {
  NORTH_AMERICA: 'North America',
  EUROPE: 'Europe',
  ASIA: 'Asia',
  SOUTH_AMERICA: 'South America',
  AFRICA: 'Africa',
  OCEANIA: 'Oceania',
  MIDDLE_EAST: 'Middle East',
  GLOBAL: 'Global',
} as const

export type Region = (typeof Region)[keyof typeof Region]

export const RiskCategory = {
  OPERATIONAL: 'Operational',
  FINANCIAL: 'Financial',
  MARKET: 'Market',
  REGULATORY: 'Regulatory',
  TECHNOLOGICAL: 'Technological',
  STRATEGIC: 'Strategic',
  COMPLIANCE: 'Compliance',
  REPUTATIONAL: 'Reputational',
  ENVIRONMENTAL: 'Environmental',
  CYBERSECURITY: 'Cybersecurity',
} as const

export type RiskCategory = (typeof RiskCategory)[keyof typeof RiskCategory]

export const RiskSeverity = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  CRITICAL: 'Critical',
} as const

export type RiskSeverity = (typeof RiskSeverity)[keyof typeof RiskSeverity]

export const PerformanceDirection = {
  INCREASED: 'Increased',
  DECREASED: 'Decreased',
  STABLE: 'Stable',
  VOLATILE: 'Volatile',
} as const

export type PerformanceDirection = (typeof PerformanceDirection)[keyof typeof PerformanceDirection]

export const OutlookSentiment = {
  POSITIVE: 'Positive',
  NEGATIVE: 'Negative',
  NEUTRAL: 'Neutral',
  CAUTIOUS: 'Cautious',
  OPTIMISTIC: 'Optimistic',
} as const

export type OutlookSentiment = (typeof OutlookSentiment)[keyof typeof OutlookSentiment]

export const LiquidityPosition = {
  STRONG: 'Strong',
  ADEQUATE: 'Adequate',
  WEAK: 'Weak',
  CRITICAL: 'Critical',
} as const

export type LiquidityPosition = (typeof LiquidityPosition)[keyof typeof LiquidityPosition]

export const DebtLevel = {
  LOW: 'Low',
  MODERATE: 'Moderate',
  HIGH: 'High',
  EXCESSIVE: 'Excessive',
} as const

export type DebtLevel = (typeof DebtLevel)[keyof typeof DebtLevel]

export const BalanceSheetTrend = {
  IMPROVING: 'Improving',
  STABLE: 'Stable',
  DECLINING: 'Declining',
  VOLATILE: 'Volatile',
} as const

export type BalanceSheetTrend = (typeof BalanceSheetTrend)[keyof typeof BalanceSheetTrend]

export const IncomeStatementTrend = {
  GROWING: 'Growing',
  STABLE: 'Stable',
  DECLINING: 'Declining',
  VOLATILE: 'Volatile',
} as const

export type IncomeStatementTrend = (typeof IncomeStatementTrend)[keyof typeof IncomeStatementTrend]

export const CashFlowTrend = {
  IMPROVING: 'Improving',
  STABLE: 'Stable',
  DECLINING: 'Declining',
  VOLATILE: 'Volatile',
} as const

export type CashFlowTrend = (typeof CashFlowTrend)[keyof typeof CashFlowTrend]

// Business Analysis Schema Types
export interface OperationalOverview {
  description: string
  industry_classification: string
  primary_markets: BusinessSegment[]
  target_customers: string | null
  business_model: string | null
}

export interface KeyProduct {
  name: string
  description: string
  significance: string | null
}

export interface CompetitiveAdvantage {
  advantage: string
  description: string
  competitors: string[] | null
  sustainability: string | null
}

export interface StrategicInitiative {
  name: string
  description: string
  impact: string
  timeframe: string | null
  resource_allocation: string | null
}

export interface BusinessSegmentDetail {
  name: string
  description: string
  segment_type: BusinessSegment
  strategic_importance: string | null
  market_position: string | null
  growth_outlook: string | null
  key_competitors: string[] | null
  relative_size: string | null
  market_trends: string | null
  product_differentiation: string | null
}

export interface GeographicSegment {
  name: string
  description: string
  region: Region
  strategic_importance: string | null
  market_position: string | null
  growth_outlook: string | null
  key_competitors: string[] | null
  relative_size: string | null
  market_characteristics: string | null
  regulatory_environment: string | null
  expansion_strategy: string | null
}

export interface SupplyChain {
  description: string
  key_suppliers: string[] | null
  sourcing_strategy: string | null
  risks: string | null
}

export interface Partnership {
  name: string
  description: string
  partnership_type: string
  strategic_value: string | null
}

export interface BusinessAnalysisSection {
  operational_overview: OperationalOverview
  key_products: KeyProduct[]
  competitive_advantages: CompetitiveAdvantage[]
  strategic_initiatives: StrategicInitiative[]
  business_segments: BusinessSegmentDetail[]
  geographic_segments: GeographicSegment[]
  supply_chain: SupplyChain | null
  partnerships: Partnership[] | null
}

// Risk Factors Analysis Schema Types
export interface RiskFactor {
  risk_name: string
  category: RiskCategory
  description: string
  severity: RiskSeverity
  probability: string | null
  potential_impact: string
  mitigation_measures: string[] | null
  timeline: string | null
}

export interface IndustryRisks {
  industry_trends: string
  competitive_pressures: string[]
  market_volatility: string | null
  disruption_threats: string[] | null
}

export interface RegulatoryRisks {
  regulatory_environment: string
  compliance_requirements: string[]
  regulatory_changes: string | null
  enforcement_risks: string | null
}

export interface FinancialRisks {
  credit_risk: string | null
  liquidity_risk: string | null
  market_risk: string | null
  interest_rate_risk: string | null
  currency_risk: string | null
}

export interface OperationalRisks {
  key_personnel_dependence: string | null
  supply_chain_disruption: string | null
  technology_failures: string | null
  quality_control: string | null
  capacity_constraints: string | null
}

export interface ESGRisks {
  environmental_risks: string[] | null
  social_responsibility: string | null
  governance_concerns: string[] | null
  sustainability_challenges: string | null
}

export interface RiskFactorsAnalysisSection {
  executive_summary: string
  risk_factors: RiskFactor[]
  industry_risks: IndustryRisks
  regulatory_risks: RegulatoryRisks
  financial_risks: FinancialRisks
  operational_risks: OperationalRisks
  esg_risks: ESGRisks | null
  risk_management_framework: string | null
  overall_risk_assessment: string
}

// Management Discussion & Analysis Schema Types
export interface KeyFinancialMetric {
  metric_name: string
  current_value: string | null
  previous_value: string | null
  direction: PerformanceDirection
  percentage_change: string | null
  explanation: string
  significance: string
}

export interface RevenueAnalysis {
  total_revenue_performance: string
  revenue_drivers: string[]
  revenue_headwinds: string[] | null
  segment_performance: string[] | null
  geographic_performance: string[] | null
  recurring_vs_onetime: string | null
}

export interface ProfitabilityAnalysis {
  gross_margin_analysis: string | null
  operating_margin_analysis: string | null
  net_margin_analysis: string | null
  cost_structure_changes: string[] | null
  efficiency_improvements: string[] | null
}

export interface LiquidityAnalysis {
  cash_position: string | null
  cash_flow_analysis: string
  working_capital: string | null
  debt_analysis: string | null
  credit_facilities: string | null
  capital_allocation: string | null
}

export interface OperationalHighlight {
  achievement: string
  impact: string
  strategic_significance: string | null
}

export interface MarketCondition {
  market_description: string
  impact_on_business: string
  competitive_dynamics: string | null
  opportunity_threats: string[] | null
}

export interface ForwardLookingStatement {
  statement: string
  metric_area: string
  timeframe: string | null
  assumptions: string[] | null
  risks_to_guidance: string[] | null
}

export interface CriticalAccountingPolicy {
  policy_name: string
  description: string
  judgment_areas: string[]
  impact_on_results: string | null
}

export interface MDAAnalysisSection {
  executive_overview: string
  key_financial_metrics: KeyFinancialMetric[]
  revenue_analysis: RevenueAnalysis
  profitability_analysis: ProfitabilityAnalysis
  liquidity_analysis: LiquidityAnalysis
  operational_highlights: OperationalHighlight[]
  market_conditions: MarketCondition[]
  forward_looking_statements: ForwardLookingStatement[] | null
  critical_accounting_policies: CriticalAccountingPolicy[] | null
  outlook_summary: string
  outlook_sentiment: OutlookSentiment
  management_priorities: string[] | null
}

// Financial Statement Analysis Schema Types
export interface AssetComposition {
  current_assets_percentage: number | null
  non_current_assets_percentage: number | null
  key_asset_categories: string[]
  asset_quality_assessment: string
}

export interface LiabilityStructure {
  current_liabilities_percentage: number | null
  long_term_debt_percentage: number | null
  debt_maturity_profile: string
  liability_concerns: string[]
}

export interface EquityAnalysis {
  total_equity_change: string
  retained_earnings_trend: string
  share_capital_changes: string
  equity_quality_assessment: string
}

export interface KeyRatio {
  ratio_name: string
  current_value: number | null
  previous_value: number | null
  industry_benchmark: number | null
  interpretation: string
}

export interface BalanceSheetAnalysisSection {
  section_summary: string
  period_covered: string
  total_assets: string | null
  total_liabilities: string | null
  total_equity: string | null
  liquidity_position: LiquidityPosition
  debt_level: DebtLevel
  overall_trend: BalanceSheetTrend
  asset_composition: AssetComposition
  liability_structure: LiabilityStructure
  equity_analysis: EquityAnalysis
  key_ratios: KeyRatio[]
  strengths: string[]
  concerns: string[]
  year_over_year_changes: string[]
  notable_items: string[]
  management_commentary: string | null
}

export interface RevenueBreakdown {
  revenue_streams: string[]
  revenue_recognition: string
  seasonal_patterns: string | null
  recurring_revenue: string | null
}

export interface ExpenseAnalysis {
  cost_of_sales: string | null
  operating_expenses: string
  non_operating_expenses: string | null
  extraordinary_items: string[] | null
}

export interface ProfitabilityMetrics {
  gross_profit_analysis: string
  operating_profit_analysis: string
  net_profit_analysis: string
  margin_trends: string[]
  profitability_drivers: string[]
}

export interface IncomeStatementAnalysisSection {
  section_summary: string
  period_covered: string
  total_revenue: string | null
  net_income: string | null
  overall_trend: IncomeStatementTrend
  revenue_breakdown: RevenueBreakdown
  expense_analysis: ExpenseAnalysis
  profitability_metrics: ProfitabilityMetrics
  key_ratios: KeyRatio[]
  strengths: string[]
  concerns: string[]
  year_over_year_changes: string[]
  notable_items: string[]
  management_commentary: string | null
}

export interface CashFlowBreakdown {
  operating_cash_flow: string
  investing_cash_flow: string
  financing_cash_flow: string
  free_cash_flow: string | null
}

export interface CashFlowQuality {
  operating_efficiency: string
  capital_allocation: string
  dividend_policy: string | null
  debt_management: string | null
}

export interface CashFlowAnalysisSection {
  section_summary: string
  period_covered: string
  net_cash_change: string | null
  overall_trend: CashFlowTrend
  cash_flow_breakdown: CashFlowBreakdown
  cash_flow_quality: CashFlowQuality
  key_ratios: KeyRatio[]
  liquidity_assessment: LiquidityPosition
  strengths: string[]
  concerns: string[]
  year_over_year_changes: string[]
  notable_items: string[]
  management_commentary: string | null
}

// Sub-Section Analysis Types
export type AnalysisSchemaData =
  | BusinessAnalysisSection
  | RiskFactorsAnalysisSection
  | MDAAnalysisSection
  | BalanceSheetAnalysisSection
  | IncomeStatementAnalysisSection
  | CashFlowAnalysisSection

export interface SubSectionAnalysisResponse {
  sub_section_name: string
  processing_time_ms: number | null
  schema_type: string
  analysis: AnalysisSchemaData
  parent_section: string
  subsection_focus: string
}

// Section Analysis Types
export interface SectionAnalysisResponse {
  section_name: string
  section_summary: string
  consolidated_insights: string[]
  overall_sentiment: number
  critical_findings: string[]
  sub_sections: SubSectionAnalysisResponse[]
  processing_time_ms: number | null
  sub_section_count: number
}

// Top-Level Comprehensive Analysis Response
export interface ComprehensiveAnalysisResponse {
  // Overall Analysis Summary
  filing_summary: string
  executive_summary: string
  key_insights: string[]
  financial_highlights: string[]
  risk_factors: string[]
  opportunities: string[]
  confidence_score: number

  // Section-Level Analysis
  section_analyses: SectionAnalysisResponse[]

  // Metadata
  total_sections_analyzed: number
  total_sub_sections_analyzed: number
  total_processing_time_ms: number | null
  filing_type: string
  company_name: string
  analysis_timestamp: string
}
