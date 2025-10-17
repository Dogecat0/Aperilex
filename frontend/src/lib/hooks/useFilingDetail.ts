import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import {
  analysisResponseSchema,
  type AnalysisResponse,
  type ComprehensionCheck,
  type HighlightCallout,
  type SectionWalkthrough,
  type StructuredAnalysisData,
  type WalkthroughPreviousComparison,
} from '@/lib/types/analysis'

type FilingDetailQueryKey = ['analysis', string | undefined, 'detail']

export interface GuidedWalkthroughSection extends SectionWalkthrough {
  highlights: HighlightCallout[]
  comprehension_checks: ComprehensionCheck[]
  previous_comparison: WalkthroughPreviousComparison | null
}

export type LessonBindingSource = 'highlight' | 'comprehension'

export interface SectionLessonBinding {
  id: string
  source: LessonBindingSource
  sectionKey: string
  walkthroughId: string
  itemId: string
  lessonId: string
  learningModuleKey: string
  moduleStage: string
  displayOrder: number
  title?: string
  summary?: string
}

export interface FilingDetailData {
  analysis: AnalysisResponse
  structured: StructuredAnalysisData | null
  guidedSections: GuidedWalkthroughSection[]
  guidedSectionsByKey: Record<string, GuidedWalkthroughSection>
  lessonBindings: SectionLessonBinding[]
  diffsBySection: Record<string, WalkthroughPreviousComparison>
}

export type UseFilingDetailOptions = Pick<
  UseQueryOptions<AnalysisResponse, unknown, FilingDetailData, FilingDetailQueryKey>,
  'enabled' | 'staleTime' | 'gcTime'
>

export function useFilingDetail(analysisId?: string, options?: UseFilingDetailOptions) {
  return useQuery({
    queryKey: ['analysis', analysisId, 'detail'] as FilingDetailQueryKey,
    queryFn: async (): Promise<AnalysisResponse> => {
      if (!analysisId) {
        throw new Error('analysisId is required to fetch a filing detail')
      }

      return apiClient.get<AnalysisResponse>(`/analyses/${analysisId}`, {
        query: { include_full_results: true },
        schema: analysisResponseSchema,
      })
    },
    select: normaliseFilingDetail,
    enabled: Boolean(analysisId) && (options?.enabled ?? true),
    staleTime: options?.staleTime,
    gcTime: options?.gcTime,
  })
}

export type UseFilingDetailReturn = ReturnType<typeof useFilingDetail>

export function normaliseFilingDetail(analysis: AnalysisResponse): FilingDetailData {
  const structured = analysis.full_results?.structured_data ?? null
  const guidedSections = extractGuidedSections(structured)
  const guidedSectionsByKey = guidedSections.reduce<Record<string, GuidedWalkthroughSection>>(
    (acc, section) => {
      acc[section.section_key] = section
      return acc
    },
    {}
  )

  const diffsBySection: Record<string, WalkthroughPreviousComparison> = {}
  for (const section of guidedSections) {
    if (section.previous_comparison) {
      diffsBySection[section.section_key] = section.previous_comparison
    }
  }

  const lessonBindings = buildLessonBindings(guidedSections)

  return {
    analysis,
    structured,
    guidedSections,
    guidedSectionsByKey,
    lessonBindings,
    diffsBySection,
  }
}

function extractGuidedSections(
  structured: StructuredAnalysisData | null
): GuidedWalkthroughSection[] {
  const walkthroughs = structured?.section_walkthroughs
  if (!walkthroughs) {
    return []
  }

  const sections: GuidedWalkthroughSection[] = []
  for (const section of Object.values(walkthroughs)) {
    const highlights = [...section.highlights].sort(
      (a, b) => a.display_order - b.display_order
    )
    const comprehensionChecks = [...section.comprehension_checks].sort(
      (a, b) => a.display_order - b.display_order
    )

    sections.push({
      ...section,
      highlights,
      comprehension_checks: comprehensionChecks,
      previous_comparison: section.previous_comparison ?? null,
    })
  }

  return sections.sort((a, b) => a.display_order - b.display_order)
}

function buildLessonBindings(sections: GuidedWalkthroughSection[]): SectionLessonBinding[] {
  const bindings: SectionLessonBinding[] = []

  for (const section of sections) {
    for (const highlight of section.highlights) {
      const reference = highlight.lesson_reference
      if (
        reference &&
        reference.lesson_id &&
        reference.learning_module_key &&
        reference.module_stage
      ) {
        bindings.push({
          id: `${section.section_key}:highlight:${highlight.id}`,
          source: 'highlight',
          sectionKey: section.section_key,
          walkthroughId: section.id,
          itemId: highlight.id,
          lessonId: reference.lesson_id,
          learningModuleKey: reference.learning_module_key,
          moduleStage: reference.module_stage,
          displayOrder: highlight.display_order,
          title: highlight.title,
          summary: highlight.summary,
        })
      }
    }

    for (const check of section.comprehension_checks) {
      const reference = check.lesson_reference
      if (
        reference &&
        reference.lesson_id &&
        reference.learning_module_key &&
        reference.module_stage
      ) {
        bindings.push({
          id: `${section.section_key}:comprehension:${check.id}`,
          source: 'comprehension',
          sectionKey: section.section_key,
          walkthroughId: section.id,
          itemId: check.id,
          lessonId: reference.lesson_id,
          learningModuleKey: reference.learning_module_key,
          moduleStage: reference.module_stage,
          displayOrder: check.display_order,
          title: check.question,
        })
      }
    }
  }

  return bindings.sort((a, b) => a.displayOrder - b.displayOrder)
}
