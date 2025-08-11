import { http, HttpResponse } from 'msw'
import type {
  CompanyResponse,
  FilingResponse,
  AnalysisResponse,
  ComprehensiveAnalysisResponse,
  HealthResponse,
  DetailedHealthResponse,
  APIError,
  PaginatedResponse,
} from '../../api/types'

// Mock API response data matching actual API types
const mockCompany: CompanyResponse = {
  company_id: '320193',
  ticker: 'AAPL',
  name: 'Apple Inc.',
  display_name: 'Apple Inc.',
  cik: '0000320193',
  sic_code: '3571',
  sic_description: 'Electronic Computers',
  industry: 'Technology',
  fiscal_year_end: '09-30',
  business_address: {
    street: '1 Apple Park Way',
    city: 'Cupertino',
    state: 'CA',
    zipcode: '95014',
    country: 'US',
  },
  recent_analyses: [
    {
      analysis_id: '1',
      analysis_template: 'comprehensive',
      created_at: '2024-01-16T10:00:00Z',
      confidence_score: 0.95,
    },
  ],
}

const mockFilings: FilingResponse[] = [
  {
    filing_id: '1',
    company_id: '320193',
    accession_number: '0000320193-24-000001',
    filing_type: '10-K',
    filing_date: '2024-01-15',
    processing_status: 'completed',
    processing_error: null,
    metadata: {
      period_end_date: '2023-12-31',
      sec_url:
        'https://www.sec.gov/Archives/edgar/data/320193/000032019324000001/aapl-20231231.htm',
      file_size: 2500000,
    },
    analyses_count: 3,
    latest_analysis_date: '2024-01-16T10:00:00Z',
  },
]

// Mock comprehensive analysis data with proper structure
const mockComprehensiveAnalysis: ComprehensiveAnalysisResponse = {
  section_analyses: [
    {
      section_name: 'Business Operations',
      section_summary:
        "Analysis of the company's core business operations and strategic initiatives.",
      overall_sentiment: 0.8,
      sub_section_count: 3,
      consolidated_insights: [
        'Strong operational efficiency across all business units',
        'Successful expansion into emerging markets',
        'Effective cost management strategies implemented',
      ],
      critical_findings: ['Supply chain optimization needed in Southeast Asia'],
      processing_time_ms: 5000,
      sub_sections: [
        {
          sub_section_name: 'Core Business Analysis',
          subsection_focus: 'Analysis of primary business segments and revenue drivers',
          schema_type: 'BusinessAnalysisSection',
          processing_time_ms: 2000,
          parent_section: 'Business Operations',
          analysis: {
            operational_overview: {
              description: 'Company operates in technology and services sectors',
              industry_classification: 'Technology',
              primary_markets: ['Technology'],
              target_customers: null,
              business_model: null,
            },
            key_products: [
              {
                name: 'Software Platform',
                description: 'Cloud-based enterprise solution',
                significance: 'Primary revenue driver accounting for 60% of total revenue',
              },
            ],
            competitive_advantages: [
              {
                advantage: 'Market Leadership',
                description: 'Leading position in enterprise software market',
                competitors: null,
                sustainability: null,
              },
            ],
            strategic_initiatives: [],
            business_segments: [],
            geographic_segments: [],
            supply_chain: null,
            partnerships: null,
          },
        },
      ],
    },
    {
      section_name: 'Risk Factors',
      section_summary:
        'Comprehensive analysis of identified risk factors and their potential impact.',
      overall_sentiment: 0.4,
      sub_section_count: 2,
      consolidated_insights: [
        'Regulatory risks increasing in key markets',
        'Cybersecurity threats require enhanced measures',
      ],
      critical_findings: [
        'Data privacy regulations may impact operations',
        'Competitive pressure intensifying',
      ],
      processing_time_ms: 3000,
      sub_sections: [
        {
          sub_section_name: 'Risk Assessment',
          subsection_focus: 'Identification and analysis of key business risks',
          schema_type: 'RiskFactorsAnalysisSection',
          processing_time_ms: 1500,
          parent_section: 'Risk Factors',
          analysis: {
            executive_summary:
              'Multiple high-severity risks identified that require immediate attention',
            risk_factors: [
              {
                risk_name: 'Regulatory Compliance',
                category: 'Regulatory',
                description: 'Evolving data privacy regulations',
                severity: 'High',
                probability: null,
                potential_impact: 'May require significant operational changes',
                mitigation_measures: null,
                timeline: null,
              },
              {
                risk_name: 'Market Competition',
                category: 'Market',
                description: 'Increasing competitive pressure',
                severity: 'Medium',
                probability: null,
                potential_impact: 'Could affect market share and pricing',
                mitigation_measures: null,
                timeline: null,
              },
            ],
            industry_risks: {
              industry_trends: 'Technology sector facing rapid changes',
              competitive_pressures: ['New market entrants', 'Price competition'],
              market_volatility: null,
              disruption_threats: null,
            },
            regulatory_risks: {
              regulatory_environment: 'Increasing regulatory scrutiny',
              compliance_requirements: ['Data privacy', 'Financial reporting'],
              regulatory_changes: null,
              enforcement_risks: null,
            },
            financial_risks: {
              credit_risk: null,
              liquidity_risk: null,
              market_risk: null,
              interest_rate_risk: null,
              currency_risk: null,
            },
            operational_risks: {
              key_personnel_dependence: null,
              supply_chain_disruption: null,
              technology_failures: null,
              quality_control: null,
              capacity_constraints: null,
            },
            esg_risks: null,
            risk_management_framework: null,
            overall_risk_assessment:
              'Moderate risk profile with specific areas requiring attention',
          },
        },
      ],
    },
    {
      section_name: 'Financial Results',
      section_summary: 'Analysis of financial performance and key metrics.',
      overall_sentiment: 0.9,
      sub_section_count: 1,
      consolidated_insights: [
        'Revenue growth acceleration in Q4',
        'Margin improvement across all segments',
      ],
      critical_findings: [],
      processing_time_ms: 2000,
      sub_sections: [],
    },
  ],
}

const mockAnalysis: AnalysisResponse = {
  analysis_id: '1',
  filing_id: '1',
  analysis_template: 'comprehensive',
  created_by: 'test-user',
  created_at: '2024-01-16T10:00:00Z',
  confidence_score: 0.95,
  llm_provider: 'openai',
  llm_model: 'gpt-4',
  processing_time_seconds: 45.2,
  filing_summary: 'Comprehensive analysis of Apple Inc. 10-K filing for fiscal year 2023.',
  executive_summary:
    'Apple continues to show strong financial performance with robust revenue growth and healthy margins.',
  key_insights: [
    'Revenue growth of 15% year-over-year driven by iPhone and Services',
    'Strong cash position of $200B+ provides financial flexibility',
    'Continued innovation in AI and services expanding market opportunities',
  ],
  risk_factors: [
    'Supply chain disruptions affecting production schedules',
    'Regulatory challenges in key international markets',
    'Intensifying competition in smartphone and services markets',
  ],
  opportunities: [
    'Expansion of AI capabilities across product ecosystem',
    'Growth potential in emerging markets',
    'Services revenue diversification opportunities',
  ],
  financial_highlights: [
    'Total revenue of $383.3 billion, up 3% year-over-year',
    'Net income of $97.0 billion with strong profit margins',
    'Cash and cash equivalents of $29.5 billion',
  ],
  sections_analyzed: 8,
  full_results: mockComprehensiveAnalysis,
}

// Additional analyses for testing different scenarios
const mockFinancialAnalysis: AnalysisResponse = {
  analysis_id: '2',
  filing_id: '2',
  analysis_template: 'financial_focused',
  created_by: 'test-user-2',
  created_at: '2024-01-14T14:30:00Z',
  confidence_score: 0.88,
  llm_provider: 'openai',
  llm_model: 'gpt-4',
  processing_time_seconds: 32,
  filing_summary: 'Financial analysis summary',
  executive_summary: 'Financial-focused analysis of quarterly results',
  key_insights: ['Profit margins improved'],
  financial_highlights: ['Net income increased'],
  risk_factors: ['Currency fluctuations'],
  opportunities: ['Cost optimization'],
  sections_analyzed: 3,
  full_results: null,
}

const mockHealthStatus: HealthResponse = {
  status: 'healthy',
  version: '1.0.0',
  environment: 'development',
  timestamp: '2024-01-16T10:00:00Z',
  message: 'All systems operational',
}

const mockHealthStatusUnhealthy: HealthResponse = {
  status: 'unhealthy',
  version: '1.0.0',
  environment: 'development',
  timestamp: '2024-01-16T10:00:00Z',
  message: 'Some services degraded',
}

const mockHealthStatusProduction: HealthResponse = {
  status: 'healthy',
  version: '2.1.0',
  environment: 'production',
  timestamp: '2024-01-16T10:00:00Z',
  message: 'All systems operational',
}

const mockDetailedHealthStatus: DetailedHealthResponse = {
  status: 'healthy',
  timestamp: '2024-01-16T10:00:00Z',
  version: '1.0.0',
  environment: 'development',
  services: {
    database: {
      status: 'healthy',
      message: 'Connected',
      timestamp: '2024-01-16T10:00:00Z',
    },
    edgar_api: {
      status: 'healthy',
      message: 'Operational',
      timestamp: '2024-01-16T10:00:00Z',
    },
    llm_provider: {
      status: 'healthy',
      message: 'OpenAI API operational',
      timestamp: '2024-01-16T10:00:00Z',
    },
  },
  configuration: {
    redis_enabled: true,
    celery_enabled: true,
    debug: true,
    redis_url_configured: true,
    celery_broker_configured: true,
  },
}

// Helper function to create CORS preflight response
const createCorsResponse = () => {
  return new HttpResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Request-ID',
      'Access-Control-Max-Age': '86400',
    },
  })
}

// Helper function to create error response
const createErrorResponse = (status: number, detail: string, error_code?: string) => {
  const error: APIError = {
    detail,
    status_code: status,
    error_code,
  }
  return HttpResponse.json(error, { status })
}

export const handlers = [
  // CORS preflight handlers - handle OPTIONS requests
  http.options('http://localhost:8000/*', () => createCorsResponse()),
  http.options('/*', () => createCorsResponse()),

  // Health check endpoints - both relative and absolute URLs
  http.get('/health', () => {
    return HttpResponse.json(mockHealthStatus)
  }),
  http.get('http://localhost:8000/health', () => {
    return HttpResponse.json(mockHealthStatus)
  }),

  // Detailed health check
  http.get('/health/detailed', () => {
    return HttpResponse.json(mockDetailedHealthStatus)
  }),
  http.get('http://localhost:8000/health/detailed', () => {
    return HttpResponse.json(mockDetailedHealthStatus)
  }),

  // Company endpoints - both relative and absolute URLs
  http.get('/api/companies/:ticker', ({ params }) => {
    return HttpResponse.json({
      ...mockCompany,
      ticker: params.ticker as string,
      display_name: `${params.ticker} Company`,
    })
  }),
  http.get('http://localhost:8000/api/companies/:ticker', ({ params }) => {
    return HttpResponse.json({
      ...mockCompany,
      ticker: params.ticker as string,
      display_name: `${params.ticker} Company`,
    })
  }),

  // Company filings endpoint (called by filingsApi.searchFilings)
  http.get('/api/companies/:ticker/filings', ({ params, request }) => {
    const url = new URL(request.url)
    const _ticker = params.ticker as string
    const _filingType = url.searchParams.get('filing_type')

    const mockPaginatedResponse = {
      data: mockFilings.map((filing) => ({
        ...filing,
        company_id: mockCompany.company_id,
      })),
      pagination: {
        page: 1,
        page_size: 10,
        total: mockFilings.length,
        total_pages: 1,
      },
    }

    return HttpResponse.json(mockPaginatedResponse)
  }),
  http.get('http://localhost:8000/api/companies/:ticker/filings', ({ params, request }) => {
    const url = new URL(request.url)
    const _ticker2 = params.ticker as string
    const _filingType2 = url.searchParams.get('filing_type')

    const mockPaginatedResponse = {
      data: mockFilings.map((filing) => ({
        ...filing,
        company_id: mockCompany.company_id,
      })),
      pagination: {
        page: 1,
        page_size: 10,
        total: mockFilings.length,
        total_pages: 1,
      },
    }

    return HttpResponse.json(mockPaginatedResponse)
  }),

  http.get('/api/companies', () => {
    return HttpResponse.json([mockCompany])
  }),
  http.get('http://localhost:8000/api/companies', () => {
    return HttpResponse.json([mockCompany])
  }),

  // Edgar filing search endpoint (called by filingsApi.searchEdgarFilings)
  http.get('/api/filings/search', ({ request }) => {
    const url = new URL(request.url)
    const ticker = url.searchParams.get('ticker')
    const formType = url.searchParams.get('form_type')

    const mockFilingResults = [
      {
        accession_number: '0000320193-24-000001',
        filing_type: formType || '10-K',
        filing_date: '2024-01-15',
        company_name: 'Apple Inc.',
        cik: '0000320193',
        ticker: ticker || 'AAPL',
        has_content: true,
        sections_count: 5,
      },
    ]

    const mockPaginatedResponse = {
      data: mockFilingResults,
      pagination: {
        page: 1,
        page_size: 10,
        total: mockFilingResults.length,
        total_pages: 1,
      },
    }

    return HttpResponse.json(mockPaginatedResponse)
  }),
  http.get('http://localhost:8000/api/filings/search', ({ request }) => {
    const url = new URL(request.url)
    const ticker = url.searchParams.get('ticker')
    const formType = url.searchParams.get('form_type')

    const mockFilingResults = [
      {
        accession_number: '0000320193-24-000001',
        filing_type: formType || '10-K',
        filing_date: '2024-01-15',
        company_name: 'Apple Inc.',
        cik: '0000320193',
        ticker: ticker || 'AAPL',
        has_content: true,
        sections_count: 5,
      },
    ]

    const mockPaginatedResponse = {
      data: mockFilingResults,
      pagination: {
        page: 1,
        page_size: 10,
        total: mockFilingResults.length,
        total_pages: 1,
      },
    }

    return HttpResponse.json(mockPaginatedResponse)
  }),

  // Filing endpoints - both relative and absolute URLs
  http.get('/api/filings', () => {
    // Return array directly for client.test.ts compatibility
    return HttpResponse.json(mockFilings)
  }),
  http.get('http://localhost:8000/api/filings', () => {
    // Return array directly for client.test.ts compatibility
    return HttpResponse.json(mockFilings)
  }),

  // Filing by accession number (called by filingsApi.getFiling)
  http.get('/api/filings/:accessionNumber', ({ params }) => {
    const param = params.accessionNumber as string
    // If it's a simple number, treat as filing_id, otherwise as accession_number
    if (/^\d+$/.test(param)) {
      return HttpResponse.json({
        ...mockFilings[0],
        filing_id: param,
      })
    }
    return HttpResponse.json({
      ...mockFilings[0],
      accession_number: param,
    })
  }),
  http.get('http://localhost:8000/api/filings/:accessionNumber', ({ params }) => {
    const param = params.accessionNumber as string
    // If it's a simple number, treat as filing_id, otherwise as accession_number
    if (/^\d+$/.test(param)) {
      return HttpResponse.json({
        ...mockFilings[0],
        filing_id: param,
      })
    }
    return HttpResponse.json({
      ...mockFilings[0],
      accession_number: param,
    })
  }),

  // Filing analysis endpoint (called by filingsApi.getFilingAnalysis)
  http.get('/api/filings/:accessionNumber/analysis', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: params.accessionNumber as string,
    })
  }),
  http.get('http://localhost:8000/api/filings/:accessionNumber/analysis', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: params.accessionNumber as string,
    })
  }),

  // Filing analyze endpoint (called by filingsApi.analyzeFiling)
  http.post('/api/filings/:accessionNumber/analyze', ({ params: _params }) => {
    const mockTask = {
      task_id: 'task-123',
      status: 'pending' as const,
      result: null,
      error_message: null,
      started_at: '2024-01-16T10:00:00Z',
      completed_at: null,
      progress_percent: 0,
      current_step: 'Initiating analysis',
    }
    return HttpResponse.json(mockTask)
  }),
  http.post(
    'http://localhost:8000/api/filings/:accessionNumber/analyze',
    ({ params: _params2 }) => {
      const mockTask = {
        task_id: 'task-123',
        status: 'pending' as const,
        result: null,
        error_message: null,
        started_at: '2024-01-16T10:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }
      return HttpResponse.json(mockTask)
    }
  ),

  // Legacy analysis endpoint pattern used by client.test.ts - return AnalysisResponse directly
  http.post('/api/filings/:ticker/:formType/analyze', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: `${params.ticker}-${params.formType}`,
      analysis_template: 'comprehensive' as const,
    })
  }),
  http.post('http://localhost:8000/api/filings/:ticker/:formType/analyze', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: `${params.ticker}-${params.formType}`,
      analysis_template: 'comprehensive' as const,
    })
  }),

  // Analysis endpoints - both relative and absolute URLs
  http.get('/api/analyses/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      analysis_id: params.id as string,
    })
  }),
  http.get('http://localhost:8000/api/analyses/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      analysis_id: params.id as string,
    })
  }),

  http.get('/api/analyses', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '20')
    const ticker = url.searchParams.get('ticker')
    const analysisType = url.searchParams.get('analysis_template')

    // Create a list of analyses for testing
    const allAnalyses = [mockAnalysis, mockFinancialAnalysis]
    let filteredAnalyses = allAnalyses

    // Apply filters
    if (ticker) {
      // For simplicity, just filter by filename containing ticker
      filteredAnalyses = allAnalyses.filter((a) => a.filing_id.includes(ticker.toLowerCase()))
    }
    if (analysisType) {
      filteredAnalyses = filteredAnalyses.filter((a) => a.analysis_template === analysisType)
    }

    const paginatedResponse: PaginatedResponse<AnalysisResponse> = {
      items: filteredAnalyses,
      pagination: {
        page,
        page_size: pageSize,
        total_items: filteredAnalyses.length,
        total_pages: Math.ceil(filteredAnalyses.length / pageSize),
        has_next: false,
        has_previous: false,
        next_page: null,
        previous_page: null,
      },
    }

    return HttpResponse.json(paginatedResponse)
  }),
  http.get('http://localhost:8000/api/analyses', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '20')
    const ticker = url.searchParams.get('ticker')
    const analysisType = url.searchParams.get('analysis_template')

    // Create a list of analyses for testing
    const allAnalyses = [mockAnalysis, mockFinancialAnalysis]
    let filteredAnalyses = allAnalyses

    // Apply filters
    if (ticker) {
      // For simplicity, just filter by filename containing ticker
      filteredAnalyses = allAnalyses.filter((a) => a.filing_id.includes(ticker.toLowerCase()))
    }
    if (analysisType) {
      filteredAnalyses = filteredAnalyses.filter((a) => a.analysis_template === analysisType)
    }

    const paginatedResponse: PaginatedResponse<AnalysisResponse> = {
      items: filteredAnalyses,
      pagination: {
        page,
        page_size: pageSize,
        total_items: filteredAnalyses.length,
        total_pages: Math.ceil(filteredAnalyses.length / pageSize),
        has_next: false,
        has_previous: false,
        next_page: null,
        previous_page: null,
      },
    }

    return HttpResponse.json(paginatedResponse)
  }),

  // Company analyses endpoints
  http.get('/api/companies/:ticker/analyses', ({ params }) => {
    return HttpResponse.json([
      {
        ...mockAnalysis,
        filing_id: `${params.ticker}-filing`,
      },
    ])
  }),
  http.get('http://localhost:8000/api/companies/:ticker/analyses', ({ params }) => {
    return HttpResponse.json([
      {
        ...mockAnalysis,
        filing_id: `${params.ticker}-filing`,
      },
    ])
  }),

  // Error handlers for testing error scenarios - both relative and absolute URLs
  http.get('/api/error/500', () => {
    return createErrorResponse(500, 'Internal Server Error', 'INTERNAL_ERROR')
  }),
  http.get('http://localhost:8000/api/error/500', () => {
    return createErrorResponse(500, 'Internal Server Error', 'INTERNAL_ERROR')
  }),

  http.get('/api/error/404', () => {
    return createErrorResponse(404, 'Resource not found', 'NOT_FOUND')
  }),
  http.get('http://localhost:8000/api/error/404', () => {
    return createErrorResponse(404, 'Resource not found', 'NOT_FOUND')
  }),

  http.get('/api/error/network', () => {
    return HttpResponse.error()
  }),
  http.get('http://localhost:8000/api/error/network', () => {
    return HttpResponse.error()
  }),

  // Dynamic test handlers that tests register
  http.get('http://localhost:8000/test-429-retry', () => {
    return HttpResponse.json({ success: true })
  }),
  http.get('http://localhost:8000/test-503-retry', () => {
    return HttpResponse.json({ success: true })
  }),
  http.get('http://localhost:8000/test-no-retry', () => {
    return HttpResponse.json({ success: true })
  }),
  http.get('http://localhost:8000/test-cancel', () => {
    return HttpResponse.json({ success: true })
  }),
  http.post('http://localhost:8000/test-json-data', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(body)
  }),
  http.get('http://localhost:8000/test-custom-headers', ({ request }) => {
    const customHeader = request.headers.get('X-Custom-Header')
    const anotherHeader = request.headers.get('X-Another-Header')
    return HttpResponse.json({ customHeader, anotherHeader })
  }),
  http.get('http://localhost:8000/test-query-params', ({ request }) => {
    const url = new URL(request.url)
    const page = url.searchParams.get('page')
    const limit = url.searchParams.get('limit')
    return HttpResponse.json({ page, limit })
  }),
  http.post('http://localhost:8000/test-post', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ method: 'POST', data: body })
  }),
  http.put('http://localhost:8000/test-put', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ method: 'PUT', data: body })
  }),
  http.patch('http://localhost:8000/test-patch', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ method: 'PATCH', data: body })
  }),
  http.delete('http://localhost:8000/test-delete', () => {
    return HttpResponse.json({ method: 'DELETE', deleted: true })
  }),
  http.get('http://localhost:8000/test-timeout', async () => {
    await new Promise((resolve) => setTimeout(resolve, 100))
    return HttpResponse.json({ success: true })
  }),
  http.get('http://localhost:8000/test-timeout-slow', async () => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return HttpResponse.json({ success: true })
  }),
]

// Export mock data for use in tests
export const mockHealthResponses = {
  healthy: mockHealthStatus,
  unhealthy: mockHealthStatusUnhealthy,
  production: mockHealthStatusProduction,
  detailed: mockDetailedHealthStatus,
}
