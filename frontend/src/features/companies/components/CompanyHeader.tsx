import React from 'react'
import { Button } from '@/components/ui/Button'
import { Building, MapPin, Calendar, BarChart3, ExternalLink } from 'lucide-react'
import type { CompanyResponse } from '@/api/types'

interface CompanyHeaderProps {
  company: CompanyResponse
  onAnalyzeFilings?: () => void
  onViewAnalyses?: () => void
}

export const CompanyHeader = React.forwardRef<HTMLDivElement, CompanyHeaderProps>(
  ({ company, onAnalyzeFilings, onViewAnalyses }, ref) => {
    return (
      <div ref={ref} className="rounded-lg border bg-card p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between space-y-4 lg:space-y-0">
          {/* Company Information */}
          <div className="space-y-4">
            {/* Company Name and Ticker */}
            <div className="space-y-2">
              <div className="flex items-center space-x-3">
                <Building className="w-8 h-8 text-primary" />
                <div>
                  <h1 className="text-2xl font-bold text-foreground">{company.display_name}</h1>
                  {company.ticker && (
                    <div className="inline-flex items-center px-3 py-1 mt-1 rounded-md bg-primary text-primary-foreground text-sm font-semibold">
                      {company.ticker}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Company Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {company.industry && (
                <div className="flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <span className="text-sm text-muted-foreground">Industry</span>
                    <p className="font-medium">{company.industry}</p>
                  </div>
                </div>
              )}

              {company.business_address && (
                <div className="flex items-center space-x-2">
                  <MapPin className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <span className="text-sm text-muted-foreground">Location</span>
                    <p className="font-medium">
                      {[
                        company.business_address.city,
                        company.business_address.state,
                        company.business_address.country,
                      ]
                        .filter(Boolean)
                        .join(', ')}
                    </p>
                  </div>
                </div>
              )}

              {company.fiscal_year_end && (
                <div className="flex items-center space-x-2">
                  <Calendar className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <span className="text-sm text-muted-foreground">Fiscal Year End</span>
                    <p className="font-medium">{company.fiscal_year_end}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center space-x-2">
                <ExternalLink className="w-5 h-5 text-muted-foreground" />
                <div>
                  <span className="text-sm text-muted-foreground">CIK</span>
                  <p className="font-medium">{company.cik}</p>
                </div>
              </div>
            </div>

            {/* SIC Information */}
            {(company.sic_code || company.sic_description) && (
              <div className="pt-4 border-t">
                <span className="text-sm text-muted-foreground">SIC Classification</span>
                <p className="font-medium">
                  {company.sic_code && `${company.sic_code} - `}
                  {company.sic_description}
                </p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row lg:flex-col space-y-2 sm:space-y-0 sm:space-x-2 lg:space-x-0 lg:space-y-2">
            {onAnalyzeFilings && (
              <Button onClick={onAnalyzeFilings} className="w-full sm:w-auto lg:w-full">
                Analyze Filings
              </Button>
            )}
            {onViewAnalyses && (
              <Button
                variant="outline"
                onClick={onViewAnalyses}
                className="w-full sm:w-auto lg:w-full"
              >
                View All Analyses
              </Button>
            )}
          </div>
        </div>

        {/* Recent Analyses Summary */}
        {company.recent_analyses && company.recent_analyses.length > 0 && (
          <div className="mt-6 pt-6 border-t">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold">Recent Activity</h3>
              <span className="text-sm text-muted-foreground">
                {company.recent_analyses.length} recent analysis
                {company.recent_analyses.length !== 1 ? 'es' : ''}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {company.recent_analyses.slice(0, 3).map((analysis) => (
                <div
                  key={analysis.analysis_id}
                  className="flex items-center justify-between p-3 rounded-md bg-secondary/50"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-primary rounded-full" />
                      <span className="text-sm font-medium">{analysis.analysis_type}</span>
                    </div>
                    {analysis.confidence_score !== undefined && (
                      <span className="text-xs text-muted-foreground">
                        Confidence: {Math.round(analysis.confidence_score * 100)}%
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(analysis.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
)

CompanyHeader.displayName = 'CompanyHeader'
