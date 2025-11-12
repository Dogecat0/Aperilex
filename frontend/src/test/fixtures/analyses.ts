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
  schema_version: 4,
  items: [
    {
      schema_version: 4,
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
  schema_version: 4,
  analysis_id: '44444444-4444-4444-4444-444444444444',
  filing_id: '55555555-5555-5555-5555-555555555555',
  analysis_type: 'COMPREHENSIVE',
  status: 'COMPLETED',
  created_at: '2025-06-12T13:45:00.000Z',
  created_by: 'analyst@aperilex.ai',
  summary: detailSummary,
  full_results: {
    schema_version: 3,
    structured_data: {
      schema_version: 3,
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
      section_walkthroughs: {
        'Item 7 - Management Discussion & Analysis': {
          id: 'walkthrough-mda',
          section_key: 'Item 7 - Management Discussion & Analysis',
          title: 'MD&A Guided Review',
          display_order: 0,
          learning_module_key: 'mda_foundations',
          module_stage: 'walkthrough',
          guidance: {
            focus: 'Connect commentary to margin movements.',
            why_it_matters:
              'Seeing how management frames margin changes sharpens your ability to explain the trend to stakeholders.',
          },
          highlights: [
            {
              id: 'highlight-mda-services',
              title: 'Services pacing profit growth',
              summary:
                'Management credits recurring services for absorbing hardware volatility and protecting margins.',
              display_order: 0,
              source_reference: 'Item 7 - Management Discussion & Analysis ¶4',
              confidence: 0.9,
              severity: null,
              lesson_reference: {
                lesson_id: 'lesson-mda-primer',
                learning_module_key: 'mda_foundations',
                module_stage: 'walkthrough',
                title: 'Breaking down MD&A narratives',
              },
              quote:
                'Services delivered double-digit growth with expanding contribution margins, stabilising total operating profit.',
              tags: ['md&a', 'margin'],
            },
            {
              id: 'highlight-mda-cost-discipline',
              title: 'Operating expense discipline',
              summary:
                'OpEx growth remained below revenue expansion, extending operating leverage despite FX pressure.',
              display_order: 1,
              source_reference: 'Item 7 - Management Discussion & Analysis ¶5',
              confidence: 0.88,
              severity: null,
              lesson_reference: {
                lesson_id: 'lesson-mda-opex',
                learning_module_key: 'mda_foundations',
                module_stage: 'walkthrough',
                title: 'Following OpEx commentary',
              },
              quote:
                'Operating expenses increased 4% while total revenue grew 8%, adding 80 bps of leverage.',
              tags: ['md&a', 'opex'],
            },
            {
              id: 'highlight-mda-cloud-scale',
              title: 'Cloud momentum offsets hardware lulls',
              summary:
                'Google Cloud and collaboration workloads delivered the largest absolute dollar growth, cushioning device cycles.',
              display_order: 2,
              source_reference: 'Item 7 - Management Discussion & Analysis ¶6',
              confidence: 0.86,
              severity: null,
              lesson_reference: {
                lesson_id: 'lesson-mda-cloud',
                learning_module_key: 'mda_foundations',
                module_stage: 'walkthrough',
                title: 'Connecting segment commentary',
              },
              quote:
                'Cloud revenue advanced 28% with expanding margins as backlog conversions accelerated.',
              tags: ['md&a', 'cloud'],
            },
            {
              id: 'highlight-mda-ai-investment',
              title: 'AI infrastructure spend front-loaded',
              summary:
                'Capex stepped up for AI-ready data centers, with management flagging near-term margin drag before monetisation catches up.',
              display_order: 3,
              source_reference: 'Item 7 - Management Discussion & Analysis ¶7',
              confidence: 0.83,
              severity: null,
              lesson_reference: {
                lesson_id: 'lesson-mda-ai-investment',
                learning_module_key: 'mda_foundations',
                module_stage: 'walkthrough',
                title: 'Evaluating AI investment pacing',
              },
              quote:
                'We expect elevated AI infrastructure spend through year-end to support Gemini and cloud demand.',
              tags: ['md&a', 'ai'],
            },
            {
              id: 'highlight-mda-capital-returns',
              title: 'Capital returns anchored by cash flow strength',
              summary:
                'Management reaffirmed buyback cadence citing $105B of cash and securities plus $16B in quarterly operating cash flow.',
              display_order: 4,
              source_reference: 'Item 7 - Management Discussion & Analysis ¶8',
              confidence: 0.87,
              severity: null,
              lesson_reference: {
                lesson_id: 'lesson-mda-capital-returns',
                learning_module_key: 'mda_foundations',
                module_stage: 'walkthrough',
                title: 'Linking cash flow to capital allocation',
              },
              quote:
                'Capital returns remain funded by operating cash flow; no incremental debt is required near term.',
              tags: ['md&a', 'capital-allocation'],
            },
          ],
          comprehension_checks: [
            {
              id: 'check-mda-margin-driver',
              question: 'Which factor most supported Apple’s margin resilience?',
              display_order: 0,
              correct_answer: 'Recurring services growth offsetting hardware softness.',
              distractors: [
                'The launch of a one-time licensing settlement.',
                'Reduced R&D spending compared to last year.',
              ],
              explanation:
                'The filing repeatedly cites services growth and disciplined costs as the reasons margins held up.',
              lesson_reference: {
                lesson_id: 'lesson-mda-margin-detection',
                learning_module_key: 'mda_foundations',
                module_stage: 'reinforce',
                title: 'Linking MD&A commentary to margins',
              },
            },
            {
              id: 'check-mda-opex-discipline',
              question: 'How did operating expenses behave relative to revenue growth?',
              display_order: 1,
              correct_answer: 'OpEx grew slower than revenue, adding leverage.',
              distractors: [
                'Operating expenses spiked faster than revenue growth.',
                'OpEx declined sharply because of hiring freezes.',
              ],
              explanation:
                'Management highlighted that operating expenses increased only 4% versus 8% revenue growth.',
              lesson_reference: {
                lesson_id: 'lesson-mda-opex',
                learning_module_key: 'mda_foundations',
                module_stage: 'reinforce',
                title: 'Tracking operating leverage',
              },
            },
            {
              id: 'check-mda-cloud-share',
              question: 'Which segment provided the largest absolute dollar growth this quarter?',
              display_order: 2,
              correct_answer: 'Google Cloud and collaboration workloads.',
              distractors: [
                'Wearables and accessories.',
                'Advertising search ads for travel customers.',
              ],
              explanation:
                'The highlight notes that cloud momentum offset device cycles by adding the most dollars.',
              lesson_reference: {
                lesson_id: 'lesson-mda-cloud',
                learning_module_key: 'mda_foundations',
                module_stage: 'reinforce',
                title: 'Connecting segment commentary',
              },
            },
            {
              id: 'check-mda-ai-capex',
              question: 'What near-term impact does AI infrastructure spending have on margins?',
              display_order: 3,
              correct_answer: 'It drags margins until monetisation catches up.',
              distractors: [
                'It immediately boosts operating margin by lowering depreciation.',
                'It eliminates the need for future capital investments entirely.',
              ],
              explanation:
                'Management emphasised front-loaded AI capex that will weigh on near-term operating margin.',
              lesson_reference: {
                lesson_id: 'lesson-mda-ai-investment',
                learning_module_key: 'mda_foundations',
                module_stage: 'reinforce',
                title: 'Evaluating AI investment pacing',
              },
            },
            {
              id: 'check-mda-capital-returns',
              question: 'Why can Apple sustain buybacks without new debt according to the filing?',
              display_order: 4,
              correct_answer: 'Operating cash flow plus cash and securities cover planned returns.',
              distractors: [
                'Management plans to suspend dividends to fund repurchases.',
                'The company sold a manufacturing plant to finance buybacks.',
              ],
              explanation:
                'The highlight states $105B of cash and $16B in operating cash flow fund the capital return program.',
              lesson_reference: {
                lesson_id: 'lesson-mda-capital-returns',
                learning_module_key: 'mda_foundations',
                module_stage: 'reinforce',
                title: 'Linking cash flow to capital allocation',
              },
            },
          ],
          estimated_duration_minutes: 9,
        },
        'Item 1A - Risk Factors': {
          id: 'walkthrough-risk',
          section_key: 'Item 1A - Risk Factors',
          title: 'Risk Factors Deep Dive',
          display_order: 1,
          learning_module_key: 'risk_mastery',
          module_stage: 'walkthrough',
          guidance: {
            focus: 'Track which risks carry high severity and what mitigations exist.',
            why_it_matters:
              'Separating high-severity items helps you prioritise diligence follow-ups and talk tracks.',
          },
          highlights: [
            {
              id: 'highlight-risk-regulation',
              title: 'Regulation pressure remains elevated',
              summary:
                'Regulators continue probing App Store policies, which Apple labels high severity given potential monetisation shifts.',
              display_order: 0,
              source_reference: 'Item 1A - Risk Factors ¶5',
              confidence: 0.84,
              severity: 'High',
              lesson_reference: {
                lesson_id: 'lesson-risk-regulation',
                learning_module_key: 'risk_mastery',
                module_stage: 'walkthrough',
                title: 'Interpreting regulatory risk language',
              },
              quote:
                'Regulatory changes could require materially different App Store economics or distribution terms.',
              tags: ['risk', 'regulation'],
            },
            {
              id: 'highlight-risk-privacy',
              title: 'Privacy frameworks evolving quickly',
              summary:
                'Management warns that regional privacy updates could limit signal quality and measurement effectiveness.',
              display_order: 1,
              source_reference: 'Item 1A - Risk Factors ¶6',
              confidence: 0.82,
              severity: 'Medium-High',
              lesson_reference: {
                lesson_id: 'lesson-risk-privacy',
                learning_module_key: 'risk_mastery',
                module_stage: 'walkthrough',
                title: 'Assessing privacy rule changes',
              },
              quote:
                'Consent requirements in the EU continue to evolve and may reduce access to user-level insights.',
              tags: ['risk', 'privacy'],
            },
            {
              id: 'highlight-risk-supply-chain',
              title: 'Supply chain concentration creates execution risk',
              summary:
                'A handful of ODM partners still account for the majority of device output, exposing launches to regional shocks.',
              display_order: 2,
              source_reference: 'Item 1A - Risk Factors ¶7',
              confidence: 0.81,
              severity: 'Medium',
              lesson_reference: {
                lesson_id: 'lesson-risk-supply-chain',
                learning_module_key: 'risk_mastery',
                module_stage: 'walkthrough',
                title: 'Evaluating supplier concentration',
              },
              quote:
                'Disruptions in a small number of Asian manufacturing partners could delay key launches.',
              tags: ['risk', 'supply-chain'],
            },
            {
              id: 'highlight-risk-ai-capacity',
              title: 'AI compute scarcity can cap growth',
              summary:
                'Alphabet relies on advanced nodes for TPU production; limited foundry capacity could constrain Gemini rollouts.',
              display_order: 3,
              source_reference: 'Item 1A - Risk Factors ¶8',
              confidence: 0.8,
              severity: 'Medium',
              lesson_reference: {
                lesson_id: 'lesson-risk-ai-capacity',
                learning_module_key: 'risk_mastery',
                module_stage: 'walkthrough',
                title: 'Understanding AI supply constraints',
              },
              quote:
                'Securing next-gen foundry slots remains critical to meeting AI demand curves.',
              tags: ['risk', 'ai'],
            },
            {
              id: 'highlight-risk-macro-demand',
              title: 'Macro-driven ad demand volatility',
              summary:
                'Advertising budgets track macro health; management flags recessionary slowdowns as a key top-line swing factor.',
              display_order: 4,
              source_reference: 'Item 1A - Risk Factors ¶9',
              confidence: 0.83,
              severity: 'Medium',
              lesson_reference: {
                lesson_id: 'lesson-risk-macro',
                learning_module_key: 'risk_mastery',
                module_stage: 'walkthrough',
                title: 'Linking macro data to ad demand',
              },
              quote:
                'A sustained macro downturn typically reduces advertiser spend, delaying ROI on new formats.',
              tags: ['risk', 'macro'],
            },
          ],
          comprehension_checks: [
            {
              id: 'check-risk-severity',
              question: 'What outcome does Apple tie to the high severity rating?',
              display_order: 0,
              correct_answer: 'Potential changes to App Store economics that impact profitability.',
              distractors: [
                'Immediate shutdown of its supply chain partners.',
                'A mandatory split of the company into separate entities.',
              ],
              explanation:
                'Apple emphasises that enforcement could force less favourable App Store terms, reducing margins.',
              lesson_reference: {
                lesson_id: 'lesson-risk-severity',
                learning_module_key: 'risk_mastery',
                module_stage: 'reinforce',
                title: 'Evaluating severity levels in filings',
              },
            },
            {
              id: 'check-risk-privacy',
              question: 'How could evolving privacy rules affect Alphabet’s ad products?',
              display_order: 1,
              correct_answer: 'Reduced signal quality that limits targeting and measurement.',
              distractors: [
                'Immediate elimination of all third-party partnerships.',
                'Guaranteed increases in conversion rates.',
              ],
              explanation:
                'The privacy highlight spells out that tougher consent rules impair targeting fidelity.',
              lesson_reference: {
                lesson_id: 'lesson-risk-privacy',
                learning_module_key: 'risk_mastery',
                module_stage: 'reinforce',
                title: 'Assessing privacy rule changes',
              },
            },
            {
              id: 'check-risk-supply-chain',
              question: 'Why does supplier concentration remain a risk?',
              display_order: 2,
              correct_answer:
                'A few ODM partners build most devices, so disruptions can delay launches.',
              distractors: [
                'Alphabet manufactures all hardware internally now.',
                'Suppliers are diversified across every continent equally.',
              ],
              explanation:
                'The highlight calls out dependence on a small set of Asian manufacturers.',
              lesson_reference: {
                lesson_id: 'lesson-risk-supply-chain',
                learning_module_key: 'risk_mastery',
                module_stage: 'reinforce',
                title: 'Evaluating supplier concentration',
              },
            },
            {
              id: 'check-risk-ai-capacity',
              question: 'What could limit Gemini and TPU growth according to the filing?',
              display_order: 3,
              correct_answer: 'Scarce advanced-node foundry capacity for AI chips.',
              distractors: [
                'User demand collapsing for AI experiences.',
                'Cloud customers refusing to sign multi-year contracts.',
              ],
              explanation:
                'The AI capacity highlight links growth plans to securing leading-edge manufacturing slots.',
              lesson_reference: {
                lesson_id: 'lesson-risk-ai-capacity',
                learning_module_key: 'risk_mastery',
                module_stage: 'reinforce',
                title: 'Understanding AI supply constraints',
              },
            },
            {
              id: 'check-risk-macro-demand',
              question: 'How does macro softness flow through to Alphabet’s revenue?',
              display_order: 4,
              correct_answer: 'Advertisers cut budgets, reducing ad spend and growth.',
              distractors: [
                'Macro weakness automatically boosts ad pricing.',
                'It triggers mandated price floors that lift revenue.',
              ],
              explanation:
                'Management states that advertising demand typically falls during recessions, pressuring growth.',
              lesson_reference: {
                lesson_id: 'lesson-risk-macro',
                learning_module_key: 'risk_mastery',
                module_stage: 'reinforce',
                title: 'Linking macro data to ad demand',
              },
            },
          ],
          estimated_duration_minutes: 7,
          previous_comparison: {
            previous_analysis_id: '99999999-8888-7777-6666-555555555555',
            previous_filing_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
            previous_sentiment: -0.05,
            current_sentiment: -0.12,
            sentiment_delta: -0.07,
            new_highlights: [
              {
                id: 'highlight-risk-regulation',
                title: 'Regulation pressure remains elevated',
                summary:
                  'Regulators continue probing App Store policies, which Apple labels high severity given potential monetisation shifts.',
                severity: 'High',
                source_reference: 'Item 1A - Risk Factors ¶5',
                confidence: 0.84,
                lesson_reference: {
                  lesson_id: 'lesson-risk-regulation',
                  learning_module_key: 'risk_mastery',
                  module_stage: 'walkthrough',
                  title: 'Interpreting regulatory risk language',
                },
              },
            ],
            dropped_highlights: [],
            pro_tip: 'New high-severity highlight detected: Regulation pressure remains elevated.',
          },
        },
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
