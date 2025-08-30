import React from 'react'
import { Button } from '@/components/ui/Button'
import { Building, MapPin, Calendar, BarChart3 } from 'lucide-react'
import type { CompanyResponse } from '@/api/types'

interface CompanyCardProps {
  company: CompanyResponse
  onViewProfile?: (ticker: string) => void
  showAnalyses?: boolean
  ticker?: string // Allow passing ticker explicitly when company.ticker is null
}

export const CompanyCard = React.forwardRef<HTMLDivElement, CompanyCardProps>(
  ({ company, onViewProfile, showAnalyses = false, ticker }, ref) => {
    const effectiveTicker = company.ticker || ticker

    const handleViewProfile = () => {
      if (onViewProfile && effectiveTicker) {
        onViewProfile(effectiveTicker)
      }
    }

    return (
      <div
        ref={ref}
        className="rounded-lg border bg-card p-6 space-y-4 hover:shadow-md transition-shadow"
      >
        {/* Company Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Building className="w-5 h-5 text-muted-foreground" />
              <h3 className="text-lg font-semibold text-foreground">{company.display_name}</h3>
            </div>
            {effectiveTicker && (
              <div className="inline-flex items-center px-2 py-1 rounded-md bg-secondary text-secondary-foreground text-sm font-medium">
                {effectiveTicker}
              </div>
            )}
          </div>
          {effectiveTicker && onViewProfile && (
            <Button variant="outline" size="sm" onClick={handleViewProfile}>
              <span className="hidden sm:inline">View Profile</span>
              <span className="sm:hidden">View</span>
            </Button>
          )}
        </div>

        {/* Company Details */}
        <div className="space-y-3">
          {company.industry && (
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <BarChart3 className="w-4 h-4" />
              <span>{company.industry}</span>
            </div>
          )}

          {company.business_address && (
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <MapPin className="w-4 h-4" />
              <span>
                {[
                  company.business_address.city,
                  company.business_address.state,
                  company.business_address.country,
                ]
                  .filter(Boolean)
                  .join(', ')}
              </span>
            </div>
          )}

          {company.fiscal_year_end && (
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Calendar className="w-4 h-4" />
              <span>Fiscal Year End: {company.fiscal_year_end}</span>
            </div>
          )}

          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <span>CIK: {company.cik}</span>
          </div>
        </div>

        {/* Recent Analyses */}
        {showAnalyses && company.recent_analyses && company.recent_analyses.length > 0 && (
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-foreground mb-2">Recent Analyses</h4>
            <div className="space-y-2">
              {company.recent_analyses.slice(0, 3).map((analysis) => (
                <div
                  key={analysis.analysis_id}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-primary rounded-full" />
                    <span className="text-muted-foreground">{analysis.analysis_template}</span>
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

CompanyCard.displayName = 'CompanyCard'
