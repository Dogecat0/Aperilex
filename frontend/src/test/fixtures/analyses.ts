import type { AnalysisResponse, PaginatedAnalysesResponse } from '@/lib/types/analysis'

const listSummary: AnalysisResponse['summary'] = {
  company: {
    name: 'Apple Inc.',
    cik: '0000320193',
    ticker: 'AAPL',
  },
  filing: {
    type: '10-Q',
    date: '2025-06-10',
    analysis_template: 'financial_focused',
  },
  confidence: {
    score: 0.87,
    bucket: 'high',
  },
  sentiment: {
    average: 0.06,
    sections: [
      { section: 'Management Discussion & Analysis', score: 0.32 },
      { section: 'Risk Factors', score: -0.18 },
      { section: 'Financial Statements', score: 0.05 },
    ],
  },
  insight_counts: {
    key_insights: 2,
    opportunities: 2,
    critical_findings: 2,
    sections_analyzed: 3,
  },
  processing: {
    duration_seconds: 42,
    completed_at: '2025-06-12T13:45:42.000Z',
  },
}

export const mockPaginatedAnalysesResponse: PaginatedAnalysesResponse = {
  schema_version: 2,
  items: [
    {
      schema_version: 2,
      analysis_id: '11111111-1111-1111-1111-111111111111',
      filing_id: '22222222-2222-2222-2222-222222222222',
      analysis_type: 'COMPREHENSIVE',
      status: 'COMPLETED',
      created_at: '2025-06-12T13:45:00.000Z',
      created_by: 'analyst@aperilex.ai',
      summary: listSummary,
      full_results: null,
    },
  ],
  pagination: {
    schema_version: 1,
    page: 1,
    page_size: 8,
    total_items: 1,
    total_pages: 1,
    has_next: false,
    has_previous: false,
    next_page: null,
    previous_page: null,
  },
}

const detailSummary: AnalysisResponse['summary'] = {
  company: {
    name: 'Apple Inc.',
    cik: '0000320193',
    ticker: 'AAPL',
  },
  filing: {
    type: '10-Q',
    date: '2025-06-10',
    analysis_template: 'financial_focused',
  },
  confidence: {
    score: 0.91,
    bucket: 'high',
  },
  sentiment: {
    average: 0.08,
    sections: [
      { section: 'Management Discussion & Analysis', score: 0.32 },
      { section: 'Risk Factors', score: -0.12 },
      { section: 'Financial Statements', score: 0.04 },
    ],
  },
  insight_counts: {
    key_insights: 2,
    opportunities: 2,
    critical_findings: 2,
    sections_analyzed: 3,
  },
  processing: {
    duration_seconds: 48,
    completed_at: '2025-06-12T13:45:48.000Z',
  },
}

export const mockAnalysisDetail: AnalysisResponse = {
  schema_version: 2,
  analysis_id: '44444444-4444-4444-4444-444444444444',
  filing_id: '55555555-5555-5555-5555-555555555555',
  analysis_type: 'COMPREHENSIVE',
  status: 'COMPLETED',
  created_at: '2025-06-12T13:45:00.000Z',
  created_by: 'analyst@aperilex.ai',
  summary: detailSummary,
  full_results: {
    schema_version: 1,
    analysis_id: '44444444-4444-4444-4444-444444444444',
    filing_id: '55555555-5555-5555-5555-555555555555',
    summary:
      'Apple Inc. delivered steady revenue growth with resilient margins driven by premium services uptake.',
    content:
      'Narrative summary: Apple Inc. posted another quarter of balanced growth driven by services and disciplined cost controls.',
    structured_data: {
      filing_summary:
        'Apple Inc. delivered steady revenue growth with resilient margins driven by premium services uptake.',
      key_insights: [
        'Services revenue accelerated while hardware stabilized.',
        'Cash flow conversion remained strong despite increased capital investment.',
      ],
      opportunities: [
        'Practice summarizing the MD&A to align with your learning goals.',
        'Track sentiment swings across the last three filings to build a comparison deck.',
      ],
      confidence_score: 0.91,
      section_analyses: [
        {
          section_name: 'Management Discussion & Analysis',
          section_summary:
            'Margin expansion stems from services mix and disciplined OpEx; management highlights supply chain resilience.',
          overall_sentiment: 0.32,
          consolidated_insights: [
            'Services mix shift improved recurring revenue visibility.',
            'Hardware demand stabilized after prior quarter volatility.',
          ],
          critical_findings: ['Watch for regional FX headwinds pressuring guidance.'],
          processing_time_ms: 11850,
          sub_section_count: 2,
          sub_sections: [
            {
              sub_section_name: 'Revenue Drivers',
              schema_type: 'revenue_trend',
              analysis: {
                metric_name: 'Total Revenue',
                current_value: 118.4,
                previous_value: 112.3,
                delta_percentage: 5.4,
                unit: 'B',
                interpretation: 'Revenue climbed 5.4% YoY, supported by services growth.',
              },
            },
            {
              sub_section_name: 'Operating Margin',
              schema_type: 'margin_profile',
              analysis: {
                metric_name: 'Operating Margin',
                current_value: 0.29,
                previous_value: 0.28,
                delta_percentage: 1.1,
                unit: '%',
                interpretation: 'Operating margin expanded 110 bps due to cost discipline.',
              },
            },
          ],
        },
        {
          section_name: 'Risk Factors',
          section_summary:
            'Supplier concentration and regulatory developments remain key watchpoints, though mitigation plans are underway.',
          overall_sentiment: -0.12,
          consolidated_insights: ['Management outlined supplier diversification milestones.'],
          critical_findings: ['Regulatory risk persists around App Store policy changes.'],
          processing_time_ms: 8450,
          sub_section_count: 1,
          sub_sections: [
            {
              sub_section_name: 'Regulatory Outlook',
              analysis: {
                metric_name: 'Regulatory Filings',
                current_value: 4,
                previous_value: 3,
                delta: 1,
                interpretation:
                  'Regulatory inquiries increased as global policy scrutiny persists.',
              },
            },
          ],
        },
        {
          section_name: 'Financial Statements',
          section_summary:
            'Cash flow to debt ratio dipped modestly due to elevated capital expenditures ahead of product launches.',
          overall_sentiment: 0.04,
          consolidated_insights: ['Inventory build tied to upcoming hardware cycle.'],
          processing_time_ms: 9020,
          sub_section_count: 2,
          sub_sections: [
            {
              sub_section_name: 'Cash Flow',
              analysis: {
                metric_name: 'Free Cash Flow',
                current_value: 28.1,
                previous_value: 29.4,
                delta_percentage: -4.4,
                unit: 'B',
                interpretation:
                  'Free cash flow softened as capex increased ahead of product refresh.',
              },
            },
            {
              sub_section_name: 'Debt Coverage',
              analysis: {
                metric_name: 'Cash-to-Debt Ratio',
                current_value: 0.92,
                previous_value: 0.97,
                delta_percentage: -5.2,
                unit: '%',
                interpretation: 'Coverage dipped but remains within historical range.',
              },
            },
          ],
        },
      ],
      total_sections_analyzed: 3,
      total_sub_sections_analyzed: 5,
      total_processing_time_ms: 29320,
      filing_type: '10-Q',
      company_name: 'Apple Inc.',
      analysis_timestamp: '2025-06-12T13:45:00.000Z',
      metadata: {
        ticker: 'AAPL',
        filing_date: '2025-06-10',
        segment: 'Consumer Electronics',
      },
    },
    status: 'COMPLETED',
    llm_provider: 'openai',
    model_name: 'gpt-4o-mini',
    processing_time_ms: 48000,
    confidence_score: 0.91,
    token_usage: {
      prompt_tokens: 13012,
      completion_tokens: 2512,
      total_tokens: 15524,
    },
    quality_metrics: {},
    metadata: {
      company_name: 'Apple Inc.',
      filing_date: '2025-06-10',
      filing_type: '10-Q',
      analysis_template: 'financial_focused',
    },
  },
}
