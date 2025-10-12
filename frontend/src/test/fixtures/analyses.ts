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
  summary_sections: [
    {
      id: 'overview-pulse',
      title: 'What to know first',
      anchor: 'overview',
      summary:
        'Services growth anchored the quarter while disciplined spending kept margins resilient.',
      supporting_points: [
        'Recurring services mix expanded share of revenue.',
        'Hardware demand stabilized after the prior supply disruption.',
      ],
    },
    {
      id: 'section-deep-dive',
      title: 'Where to dive deeper',
      anchor: 'sections',
      summary:
        'Focus on Management Discussion & Analysis to connect the qualitative narrative with execution updates.',
      supporting_points: [
        'MD&A outlines the cost discipline behind the margin expansion.',
        'Risk Factors detail regulatory scrutiny that could pressure guidance.',
      ],
      cta_label: 'Open sections tab',
    },
    {
      id: 'metric-scan',
      title: 'Numbers to watch',
      anchor: 'numbers',
      summary:
        'Top-line and operating leverage remain the headline metrics with FX volatility as the swing factor.',
      supporting_points: [
        'Total revenue climbed 5.4% year over year.',
        'Operating margin widened by one percentage point.',
      ],
    },
    {
      id: 'sentiment-check',
      title: 'Sentiment pulse',
      anchor: 'sentiment',
      summary:
        'Overall tone is positive, though Risk Factors trend weaker as regulators probe App Store policy.',
      supporting_points: [
        'Risk Factors posted the lowest sentiment at -0.18.',
        'MD&A sentiment remains constructive on execution.',
      ],
    },
  ],
  filing_summary:
    'Apple delivered steady revenue growth with resilient margins supported by premium services.',
  key_insights: [
    'Services revenue accelerated while hardware stabilized.',
    'Cash flow conversion remained strong despite increased capital investment.',
  ],
  critical_findings: ['FX volatility remains a near-term watchpoint for guidance.'],
  opportunities: ['Expand enterprise services bundles to deepen recurring revenue.'],
  headline_metrics: [
    {
      id: 'total_revenue',
      name: 'Total Revenue',
      category: 'growth',
      unit: 'B',
      current_value: 118.4,
      previous_value: 112.3,
      delta_value: 6.1,
      display: {
        current: '$118.4B',
        previous: '$112.3B',
        delta: '+$6.1B',
        delta_text: 'Revenue climbed $6.1B versus prior-year quarter on services momentum.',
      },
      confidence: 0.9,
    },
  ],
  risk_highlights: {
    critical_actions: [
      {
        id: 'fx-headwinds',
        title: 'Currency volatility threatens guidance',
        severity: 'high',
        probability: 'medium',
        summary: 'Regional FX swings could compress near-term revenue targets.',
        recommended_action: 'Refresh hedging program before Q4 close.',
        related_sections: ['Management Discussion & Analysis'],
      },
    ],
    signals_to_monitor: [
      {
        id: 'app-store-scrutiny',
        title: 'App Store policy scrutiny persists',
        severity: 'medium',
        probability: 'medium',
        summary: 'Global regulators continue to review App Store economics.',
        recommended_action: 'Maintain regulator touchpoints and update compliance roadmap.',
        related_sections: ['Risk Factors'],
      },
    ],
  },
  insight_timeline: [
    {
      id: 'timeline-revenue',
      occurred_at: '2025-06-10T00:00:00Z',
      type: 'metric',
      severity: 'medium',
      title: 'Revenue up 5.4% YoY',
      summary: 'Services momentum accelerated total revenue expansion.',
      source_section: 'Management Discussion & Analysis',
      related_metrics: ['total_revenue'],
    },
    {
      id: 'timeline-fx',
      occurred_at: '2025-06-10T00:05:00Z',
      type: 'risk',
      severity: 'high',
      title: 'FX headwinds risk surfaces',
      summary: 'Currency volatility may pressure upcoming guidance.',
      source_section: 'Risk Factors',
    },
  ],
  sentiment_rollup: {
    overall: 0.12,
    weakest_section: { section: 'Risk Factors', score: -0.18 },
    previous_overall: 0.18,
    prior_analysis_delta: -0.06,
    trend: 'down',
    confidence_band: 'medium',
  },
}

export const mockPaginatedAnalysesResponse: PaginatedAnalysesResponse = {
  schema_version: 3,
  items: [
    {
      schema_version: 3,
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
  summary_sections: [
    {
      id: 'overview-primer',
      title: 'Quick read',
      anchor: 'overview',
      summary:
        'Apple balanced services momentum with disciplined OpEx, keeping profitability on track.',
      supporting_points: [
        'Recurring services revenue continues to expand share.',
        'Management signalled confidence in supply resilience.',
      ],
    },
    {
      id: 'section-follow-up',
      title: 'Where to focus',
      anchor: 'sections',
      summary:
        'Start in MD&A for execution details, then review Risk Factors for regulatory exposure tracking.',
      supporting_points: [
        'MD&A details the cost controls that supported margin gains.',
        'Risk Factors outline regulatory and FX watchpoints.',
      ],
      cta_label: 'Review sections',
    },
    {
      id: 'numbers-overview',
      title: 'Metric watchlist',
      anchor: 'numbers',
      summary:
        'Track total revenue, operating margin, and FX impact to understand quarter-to-quarter leverage.',
      supporting_points: [
        'Revenue increased 5.4% YoY on services mix.',
        'Operating margin expanded one point thanks to cost discipline.',
      ],
    },
    {
      id: 'sentiment-trend',
      title: 'Sentiment snapshot',
      anchor: 'sentiment',
      summary:
        'Sentiment remains net positive with MD&A leading, but Risk Factors soften on regulatory pressure.',
      supporting_points: [
        'Overall sentiment registered at 0.14.',
        'Risk Factors scored -0.12, marking the weakest tone.',
      ],
    },
  ],
  filing_summary:
    'Apple posted another quarter of balanced growth driven by services mix shift and disciplined operating expenses.',
  key_insights: [
    'Services revenue accelerated to double-digit growth, improving recurring visibility.',
    'Hardware demand stabilized after supply chain volatility, supporting margin resilience.',
  ],
  critical_findings: ['Watch for regional FX headwinds pressuring guidance.'],
  opportunities: [
    'Explore bundling enterprise services to deepen adoption in regulated industries.',
    'Leverage product launch momentum to expand high-margin accessory attach rates.',
  ],
  headline_metrics: [
    {
      id: 'total_revenue',
      name: 'Total Revenue',
      category: 'growth',
      unit: 'B',
      current_value: 118.4,
      previous_value: 112.3,
      delta_value: 6.1,
      display: {
        current: '$118.4B',
        previous: '$112.3B',
        delta: '+$6.1B',
        delta_text: 'Revenue climbed $6.1B versus prior-year quarter on services momentum.',
      },
      confidence: 0.92,
    },
    {
      id: 'operating_margin',
      name: 'Operating Margin',
      category: 'profitability',
      unit: '%',
      current_value: 0.29,
      previous_value: 0.28,
      delta_value: 0.01,
      display: {
        current: '29%',
        previous: '28%',
        delta: '+1 pt',
        delta_text: 'Operating margin expanded one point due to disciplined OpEx.',
      },
      confidence: 0.88,
    },
  ],
  risk_highlights: {
    critical_actions: [
      {
        id: 'fx-headwinds',
        title: 'FX headwinds threaten guidance',
        severity: 'high',
        probability: 'medium',
        summary: 'Currency volatility could compress guidance in the next quarter.',
        recommended_action: 'Refresh hedging program and update guidance sensitivity.',
        related_sections: ['Management Discussion & Analysis', 'Risk Factors'],
      },
    ],
    signals_to_monitor: [
      {
        id: 'app-store-compliance',
        title: 'App Store compliance scrutiny',
        severity: 'medium',
        probability: 'medium',
        summary: 'Global regulators continue to evaluate App Store economics and fees.',
        recommended_action: 'Maintain regulator touchpoints and scenario plans.',
        related_sections: ['Risk Factors'],
      },
    ],
  },
  insight_timeline: [
    {
      id: 'timeline-revenue',
      occurred_at: '2025-06-10T00:00:00Z',
      type: 'metric',
      severity: 'medium',
      title: 'Revenue up 5.4% YoY',
      summary: 'Services momentum accelerated total revenue expansion.',
      source_section: 'Management Discussion & Analysis',
      related_metrics: ['total_revenue'],
    },
    {
      id: 'timeline-risk',
      occurred_at: '2025-06-10T00:05:00Z',
      type: 'risk',
      severity: 'high',
      title: 'FX headwinds risk surfaces',
      summary: 'Currency volatility may pressure upcoming guidance without hedging adjustments.',
      source_section: 'Risk Factors',
      actions: ['Refresh hedging strategy'],
    },
  ],
  sentiment_rollup: {
    overall: 0.14,
    weakest_section: { section: 'Risk Factors', score: -0.12 },
    previous_overall: 0.2,
    prior_analysis_delta: -0.06,
    trend: 'down',
    confidence_band: 'medium',
  },
}

export const mockAnalysisDetail: AnalysisResponse = {
  schema_version: 3,
  analysis_id: '44444444-4444-4444-4444-444444444444',
  filing_id: '55555555-5555-5555-5555-555555555555',
  analysis_type: 'COMPREHENSIVE',
  status: 'COMPLETED',
  created_at: '2025-06-12T13:45:00.000Z',
  created_by: 'analyst@aperilex.ai',
  summary: detailSummary,
  full_results: {
    schema_version: 2,
    structured_data: {
      schema_version: 2,
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
    provider: {
      name: 'openai',
      model_name: 'gpt-4o-mini',
      model_version: null,
      token_usage: {
        prompt_tokens: 13012,
        completion_tokens: 2512,
        total_tokens: 15524,
      },
      processing: {
        time_ms: 48000,
        started_at: '2025-06-12T13:42:00.000Z',
        completed_at: '2025-06-12T13:45:00.000Z',
      },
      confidence_score: 0.91,
      estimated_cost: 5.44,
      metadata: {
        company_name: 'Apple Inc.',
        filing_date: '2025-06-10',
        filing_type: '10-Q',
        analysis_template: 'financial_focused',
      },
    },
    narrative: {
      content:
        'Narrative summary: Apple Inc. posted another quarter of balanced growth driven by services and disciplined cost controls.',
    },
  },
}
