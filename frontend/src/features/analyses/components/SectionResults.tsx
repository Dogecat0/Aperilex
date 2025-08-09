import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Target,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Building,
  Shield,
  Users,
} from 'lucide-react'
import type { SectionAnalysisResponse } from '@/api/types'
import { SubSectionRenderer } from '@/components/analysis/SubSectionRenderer'

interface SectionResultsProps {
  sections: SectionAnalysisResponse[]
}

export function SectionResults({ sections }: SectionResultsProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  const toggleSection = (sectionName: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionName)) {
      newExpanded.delete(sectionName)
    } else {
      newExpanded.add(sectionName)
    }
    setExpandedSections(newExpanded)
  }

  const getSectionIcon = (sectionName: string) => {
    const name = sectionName.toLowerCase()
    if (name.includes('business')) return Building
    if (name.includes('risk')) return AlertTriangle
    if (name.includes('mda') || name.includes('management')) return Users
    if (name.includes('balance')) return DollarSign
    if (name.includes('income')) return TrendingUp
    if (name.includes('cash')) return Shield
    return Target
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment >= 0.6) return 'text-success bg-success/10 border-success/20'
    if (sentiment >= 0.4) return 'text-warning bg-warning/10 border-warning/20'
    if (sentiment >= 0.2) return 'text-warning bg-warning/10 border-warning/20'
    return 'text-destructive bg-destructive/10 border-destructive/20'
  }

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment >= 0.8) return 'Very Positive'
    if (sentiment >= 0.6) return 'Positive'
    if (sentiment >= 0.4) return 'Neutral'
    if (sentiment >= 0.2) return 'Cautious'
    return 'Negative'
  }

  const renderSubSectionContent = (subSection: any) => {
    const { schema_type, analysis, sub_section_name } = subSection

    return (
      <SubSectionRenderer
        schemaType={schema_type}
        analysis={analysis}
        subSectionName={sub_section_name}
        parentSection={subSection.section_name}
      />
    )
  }

  if (!sections || sections.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border shadow-sm p-6">
        <div className="text-center py-8">
          <Target className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">
            No Section Analysis Available
          </h3>
          <p className="text-muted-foreground">
            This analysis doesn't contain detailed section-by-section results.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-lg border border-border shadow-sm">
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Comprehensive Section Analysis
              </h2>
              <p className="text-muted-foreground text-sm mt-1">
                Detailed analysis of {sections.length} filing sections with{' '}
                {sections.reduce((acc, s) => acc + s.sub_section_count, 0)} sub-sections
              </p>
            </div>
          </div>
        </div>

        <div className="divide-y divide-border">
          {sections.map((section, _index) => {
            const isExpanded = expandedSections.has(section.section_name)
            const SectionIcon = getSectionIcon(section.section_name)

            return (
              <div key={section.section_name} className="p-6">
                <button
                  onClick={() => toggleSection(section.section_name)}
                  className="w-full flex items-center justify-between text-left hover:bg-muted/50 -m-2 p-2 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                      <SectionIcon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-foreground truncate">
                        {section.section_name}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <div
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getSentimentColor(section.overall_sentiment)}`}
                        >
                          {getSentimentLabel(section.overall_sentiment)}
                        </div>
                        {section.sub_section_count > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {section.sub_section_count} sub-sections
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-5 w-5 text-muted-foreground/50 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-muted-foreground/50 flex-shrink-0" />
                  )}
                </button>

                {isExpanded && (
                  <div className="mt-6 ml-13 space-y-6">
                    {/* Critical Findings - Keep as high-level summary */}
                    {section.critical_findings && section.critical_findings.length > 0 && (
                      <div>
                        <h4 className="font-medium text-foreground mb-3 flex items-center gap-2">
                          Critical Findings
                        </h4>
                        <ul className="space-y-2">
                          {section.critical_findings.map((finding, findingIndex) => (
                            <li key={findingIndex} className="flex gap-2">
                              <div className="w-1.5 h-1.5 bg-destructive rounded-full mt-2 flex-shrink-0"></div>
                              <span className="text-foreground/80">{finding}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Sub-Sections - Streamlined presentation */}
                    {section.sub_sections && section.sub_sections.length > 0 && (
                      <div>
                        <h4 className="font-medium text-foreground mb-4">
                          Detailed Sub-Section Analysis
                        </h4>
                        <div className="space-y-6">
                          {section.sub_sections.map((subSection, subIndex) => (
                            <div
                              key={subIndex}
                              className="bg-card border border-border rounded-lg overflow-hidden"
                            >
                              {/* Dedicated component renders complete content */}
                              <div className="p-4">{renderSubSectionContent(subSection)}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
