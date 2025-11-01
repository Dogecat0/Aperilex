import { z } from 'zod'

export const analysisTypeSchema = z.enum([
  'COMPREHENSIVE',
  'FINANCIAL',
  'RISK',
  'COMPETITION',
  'BUSINESS',
  'TREND',
  'SENTIMENT',
  'CUSTOM',
])

export type AnalysisType = z.infer<typeof analysisTypeSchema>

export const analysisStatusSchema = z.enum([
  'PENDING',
  'QUEUED',
  'IN_PROGRESS',
  'ANALYZING',
  'INITIATED',
  'FETCHING',
  'PARSING',
  'STORING',
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'ERROR',
  'EXPIRED',
])

export type AnalysisStatus = z.infer<typeof analysisStatusSchema>

export const tokenUsageSchema = z
  .object({
    prompt_tokens: z.number().int().nonnegative().optional(),
    completion_tokens: z.number().int().nonnegative().optional(),
    total_tokens: z.number().int().nonnegative().optional(),
  })
  .strict()

export type TokenUsage = z.infer<typeof tokenUsageSchema>

export const subsectionAnalysisSchema = z
  .object({
    sub_section_name: z.string(),
    schema_type: z.string().nullable().optional(),
    subsection_focus: z.string().nullable().optional(),
    processing_time_ms: z.number().int().optional(),
    analysis: z.unknown().optional(),
    parent_section: z.string().optional(),
  })
  .passthrough()

export type SubsectionAnalysis = z.infer<typeof subsectionAnalysisSchema>

export const sectionAnalysisSchema = z
  .object({
    section_name: z.string(),
    section_summary: z.string().nullable().optional(),
    overall_sentiment: z.number().min(-1).max(1).nullable().optional(),
    consolidated_insights: z.array(z.string()).optional(),
    critical_findings: z.array(z.string()).optional(),
    processing_time_ms: z.number().int().nonnegative().optional(),
    sub_section_count: z.number().int().nonnegative().optional(),
    sub_sections: z.array(subsectionAnalysisSchema).optional(),
  })
  .passthrough()

export type SectionAnalysis = z.infer<typeof sectionAnalysisSchema>

export const STRUCTURED_ANALYSIS_SCHEMA_VERSION = 3

export const lessonReferenceSchema = z
  .object({
    lesson_id: z.string(),
    learning_module_key: z.string(),
    module_stage: z.string(),
    title: z.string().nullable().optional(),
  })
  .strict()

export type LessonReference = z.infer<typeof lessonReferenceSchema>

export const walkthroughGuidanceSchema = z
  .object({
    focus: z.string(),
    why_it_matters: z.string(),
  })
  .strict()

export type WalkthroughGuidance = z.infer<typeof walkthroughGuidanceSchema>

export const highlightCalloutSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    summary: z.string(),
    display_order: z.number().int().min(0),
    source_reference: z.string(),
    confidence: z.number().min(0).max(1).nullable().optional(),
    severity: z.string().nullable().optional(),
    lesson_reference: lessonReferenceSchema.optional(),
    quote: z.string().nullable().optional(),
    tags: z.array(z.string()).default([]),
  })
  .strict()

export type HighlightCallout = z.infer<typeof highlightCalloutSchema>

export const diffLessonReferenceSchema = z
  .object({
    lesson_id: z.string().nullable().optional(),
    learning_module_key: z.string().nullable().optional(),
    module_stage: z.string().nullable().optional(),
    title: z.string().nullable().optional(),
  })
  .strict()

export type DiffLessonReference = z.infer<typeof diffLessonReferenceSchema>

export const walkthroughDiffHighlightSchema = z
  .object({
    id: z.string().nullable().optional(),
    title: z.string().nullable().optional(),
    summary: z.string().nullable().optional(),
    severity: z.string().nullable().optional(),
    source_reference: z.string().nullable().optional(),
    confidence: z.number().nullable().optional(),
    lesson_reference: diffLessonReferenceSchema.nullable().optional(),
  })
  .strict()

export type WalkthroughDiffHighlight = z.infer<typeof walkthroughDiffHighlightSchema>

export const walkthroughPreviousComparisonSchema = z
  .object({
    previous_analysis_id: z.string().nullable().optional(),
    previous_filing_id: z.string().nullable().optional(),
    previous_sentiment: z.number().nullable().optional(),
    current_sentiment: z.number().nullable().optional(),
    sentiment_delta: z.number().nullable().optional(),
    new_highlights: z.array(walkthroughDiffHighlightSchema).default([]),
    dropped_highlights: z.array(walkthroughDiffHighlightSchema).default([]),
    pro_tip: z.string().nullable().optional(),
  })
  .passthrough()

export type WalkthroughPreviousComparison = z.infer<typeof walkthroughPreviousComparisonSchema>

export const comprehensionCheckSchema = z
  .object({
    id: z.string(),
    question: z.string(),
    display_order: z.number().int().min(0),
    correct_answer: z.string(),
    distractors: z.array(z.string()).min(2),
    explanation: z.string(),
    lesson_reference: lessonReferenceSchema.optional(),
  })
  .strict()

export type ComprehensionCheck = z.infer<typeof comprehensionCheckSchema>

export const sectionWalkthroughSchema = z
  .object({
    id: z.string(),
    section_key: z.string(),
    title: z.string(),
    display_order: z.number().int().min(0),
    learning_module_key: z.string(),
    module_stage: z.string(),
    guidance: walkthroughGuidanceSchema,
    highlights: z.array(highlightCalloutSchema),
    comprehension_checks: z.array(comprehensionCheckSchema),
    estimated_duration_minutes: z.number().int().positive().optional(),
    previous_comparison: walkthroughPreviousComparisonSchema.nullable().optional(),
  })
  .strict()

export type SectionWalkthrough = z.infer<typeof sectionWalkthroughSchema>

export const structuredAnalysisDataSchema = z
  .object({
    schema_version: z.number().int().min(1).default(STRUCTURED_ANALYSIS_SCHEMA_VERSION),
    filing_summary: z.string().optional(),
    key_insights: z.array(z.string()).optional(),
    opportunities: z.array(z.string()).optional(),
    confidence_score: z.number().min(0).max(1).optional(),
    section_analyses: z.array(sectionAnalysisSchema).optional(),
    total_sections_analyzed: z.number().int().nonnegative().optional(),
    total_sub_sections_analyzed: z.number().int().nonnegative().optional(),
    total_processing_time_ms: z.number().int().nonnegative().optional(),
    filing_type: z.string().optional(),
    company_name: z.string().optional(),
    analysis_timestamp: z.string().optional(),
    metadata: z.record(z.unknown()).optional(),
    section_walkthroughs: z.record(sectionWalkthroughSchema).default({}),
  })
  .passthrough()

export type StructuredAnalysisData = z.infer<typeof structuredAnalysisDataSchema>

const providerProcessingSchema = z
  .object({
    time_ms: z.number().int().nonnegative(),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
  })
  .passthrough()

const providerMetadataSchema = z
  .object({
    name: z.string(),
    model_name: z.string(),
    model_version: z.string().nullable().optional(),
    token_usage: tokenUsageSchema,
    processing: providerProcessingSchema,
    confidence_score: z.number().min(0).max(1).nullable().optional(),
    estimated_cost: z.number().nullable().optional(),
    quality_metrics: z.record(z.number()).optional(),
    metadata: z.record(z.unknown()).optional(),
  })
  .passthrough()

const narrativeArtifactSchema = z
  .object({
    content: z.string().nullable().optional(),
    citations: z.array(z.record(z.unknown())).optional(),
  })
  .passthrough()

export const analysisFullResultsSchema = z
  .object({
    schema_version: z.number().int(),
    structured_data: structuredAnalysisDataSchema.nullable().optional(),
    provider: providerMetadataSchema,
    narrative: narrativeArtifactSchema.optional(),
  })
  .passthrough()

export type AnalysisFullResults = z.infer<typeof analysisFullResultsSchema>

const companySummarySchema = z
  .object({
    name: z.string().nullable().optional(),
    cik: z.string().nullable().optional(),
    ticker: z.string().nullable().optional(),
    exchange: z.string().nullable().optional(),
    industry: z.string().nullable().optional(),
  })
  .strict()

const filingSummarySchema = z
  .object({
    type: z.string().nullable().optional(),
    date: z.string().nullable().optional(),
    analysis_template: z.string().nullable().optional(),
    accession_number: z.string().nullable().optional(),
  })
  .strict()

const confidenceSummarySchema = z
  .object({
    score: z.number().min(0).max(1).nullable().optional(),
    bucket: z.string().nullable().optional(),
  })
  .strict()

const sentimentSectionSchema = z
  .object({
    section: z.string(),
    score: z.number().min(-1).max(1).nullable().optional(),
  })
  .strict()

const sentimentSummarySchema = z
  .object({
    average: z.number().min(-1).max(1).nullable().optional(),
    sections: z.array(sentimentSectionSchema).optional(),
  })
  .strict()

const insightCountsSchema = z
  .object({
    key_insights: z.number().int().nonnegative().nullable().optional(),
    opportunities: z.number().int().nonnegative().nullable().optional(),
    critical_findings: z.number().int().nonnegative().nullable().optional(),
    sections_analyzed: z.number().int().nonnegative().nullable().optional(),
  })
  .strict()

const processingSummarySchema = z
  .object({
    duration_seconds: z.number().nonnegative().nullable().optional(),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
  })
  .strict()

const headlineMetricDisplaySchema = z
  .object({
    current: z.string().nullable().optional(),
    previous: z.string().nullable().optional(),
    delta: z.string().nullable().optional(),
    delta_text: z.string().nullable().optional(),
  })
  .strict()

export const headlineMetricSchema = z
  .object({
    id: z.string().nullable().optional(),
    name: z.string(),
    category: z.string().nullable().optional(),
    unit: z.string().nullable().optional(),
    current_value: z.number().nullable().optional(),
    previous_value: z.number().nullable().optional(),
    delta_value: z.number().nullable().optional(),
    display: headlineMetricDisplaySchema.optional(),
    confidence: z.number().min(0).max(1).nullable().optional(),
  })
  .strict()

export type HeadlineMetric = z.infer<typeof headlineMetricSchema>

const weakestSentimentSectionSchema = z
  .object({
    section: z.string(),
    score: z.number().min(-1).max(1).nullable().optional(),
  })
  .strict()

const sentimentRollupSchema = z
  .object({
    overall: z.number().min(-1).max(1).nullable().optional(),
    weakest_section: weakestSentimentSectionSchema.nullable().optional(),
    previous_overall: z.number().min(-1).max(1).nullable().optional(),
    prior_analysis_delta: z.number().nullable().optional(),
    trend: z.string().nullable().optional(),
    confidence_band: z.string().nullable().optional(),
    pro_tip: z.string().nullable().optional(),
  })
  .strict()

export type SentimentRollup = z.infer<typeof sentimentRollupSchema>

const summarySegmentFeaturedMetricSchema = z
  .object({
    id: z.string(),
    label: z.string(),
    current: z.string().nullable().optional(),
    delta: z.string().nullable().optional(),
    trend: z.enum(['up', 'down', 'flat']).nullable().optional(),
  })
  .strict()

const summarySectionSchema = z
  .object({
    id: z.string().nullable().optional(),
    title: z.string(),
    anchor: z.string(),
    summary: z.string().nullable().optional(),
    supporting_points: z.array(z.string()).optional(),
    featured_metric: summarySegmentFeaturedMetricSchema.nullable().optional(),
    cta_label: z.string().nullable().optional(),
  })
  .passthrough()

export type SummarySection = z.infer<typeof summarySectionSchema>
export type SummarySegmentFeaturedMetric = z.infer<typeof summarySegmentFeaturedMetricSchema>

export const analysisSummarySchema = z
  .object({
    company: companySummarySchema,
    filing: filingSummarySchema,
    confidence: confidenceSummarySchema.optional(),
    sentiment: sentimentSummarySchema.optional(),
    insight_counts: insightCountsSchema.optional(),
    processing: processingSummarySchema.optional(),
    filing_summary: z.string().nullable().optional(),
    key_insights: z.array(z.string()).optional(),
    opportunities: z.array(z.string()).optional(),
    critical_findings: z.array(z.string()).optional(),
    headline_metrics: z.array(headlineMetricSchema).optional(),
    sentiment_rollup: sentimentRollupSchema.optional(),
    links: z.record(z.string(), z.string()).optional(),
    tags: z.array(z.string()).optional(),
    summary_sections: z.array(summarySectionSchema).optional(),
  })
  .passthrough()

export type AnalysisSummary = z.infer<typeof analysisSummarySchema>

export const analysisResponseSchema = z
  .object({
    schema_version: z.number().int().min(1),
    analysis_id: z.string().uuid(),
    filing_id: z.string().uuid(),
    analysis_type: analysisTypeSchema,
    status: analysisStatusSchema,
    created_by: z.string().nullable().optional(),
    created_at: z.string(),
    summary: analysisSummarySchema,
    full_results: analysisFullResultsSchema.nullable().optional(),
  })
  .passthrough()

export type AnalysisResponse = z.infer<typeof analysisResponseSchema>

export const paginationMetadataSchema = z
  .object({
    schema_version: z.number().int().min(1).default(1),
    page: z.number().int().min(1),
    page_size: z.number().int().min(1),
    total_items: z.number().int().min(0),
    total_pages: z.number().int().min(0),
    has_next: z.boolean(),
    has_previous: z.boolean(),
    next_page: z.number().int().min(1).nullable().optional(),
    previous_page: z.number().int().min(1).nullable().optional(),
  })
  .strict()

export type PaginationMetadata = z.infer<typeof paginationMetadataSchema>

export const paginatedAnalysesSchema = z
  .object({
    schema_version: z.number().int().min(1),
    items: z.array(analysisResponseSchema),
    pagination: paginationMetadataSchema,
  })
  .passthrough()

export type PaginatedAnalysesResponse = z.infer<typeof paginatedAnalysesSchema>

export interface ListAnalysesParams {
  search?: string
  segment?: 'all' | 'attention' | 'ready_for_review' | 'flagged'
  status?: string
  created_after?: string
  created_before?: string
  created_by?: string
  sort?: 'created_at' | 'confidence_score' | 'insight_counts.critical_findings'
  direction?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface GetAnalysisOptions {
  include_full_results?: boolean
}
