import { http, HttpResponse } from 'msw'
import type {
  CompanyResponse,
  FilingResponse,
  AnalysisResponse,
  HealthResponse,
  DetailedHealthResponse,
  APIError,
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
      analysis_type: 'COMPREHENSIVE',
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

const mockAnalysis: AnalysisResponse = {
  analysis_id: '1',
  filing_id: '1',
  analysis_type: 'COMPREHENSIVE',
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
  full_results: {
    sections: [
      {
        section_name: 'Business Overview',
        summary:
          'Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.',
        key_points: [
          'Leading market position in premium segments',
          'Strong brand loyalty and ecosystem integration',
        ],
        sentiment: 'positive',
        confidence: 0.92,
      },
    ],
    overall_sentiment: 'positive',
    metadata: {
      total_sections: 8,
      processing_duration: 45.2,
    },
  },
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

  http.get('/api/companies', () => {
    return HttpResponse.json([mockCompany])
  }),
  http.get('http://localhost:8000/api/companies', () => {
    return HttpResponse.json([mockCompany])
  }),

  // Filing endpoints - both relative and absolute URLs
  http.get('/api/filings', () => {
    return HttpResponse.json(mockFilings)
  }),
  http.get('http://localhost:8000/api/filings', () => {
    return HttpResponse.json(mockFilings)
  }),

  http.get('/api/filings/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockFilings[0],
      filing_id: params.id as string,
    })
  }),
  http.get('http://localhost:8000/api/filings/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockFilings[0],
      filing_id: params.id as string,
    })
  }),

  // Analysis creation endpoint - both relative and absolute URLs
  http.post('/api/filings/:ticker/:formType/analyze', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: `${params.ticker}-${params.formType}`,
    })
  }),
  http.post('http://localhost:8000/api/filings/:ticker/:formType/analyze', ({ params }) => {
    return HttpResponse.json({
      ...mockAnalysis,
      filing_id: `${params.ticker}-${params.formType}`,
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

  http.get('/api/analyses', () => {
    return HttpResponse.json([mockAnalysis])
  }),
  http.get('http://localhost:8000/api/analyses', () => {
    return HttpResponse.json([mockAnalysis])
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
