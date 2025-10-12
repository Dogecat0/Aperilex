import type { SubsectionAnalysis } from '@/lib/types/analysis'
import type { ParsedSubsection, SubsectionSchemaType } from '@/lib/types/analysisSchemas'

export type SentimentTone = 'positive' | 'neutral' | 'negative'

export interface SubsectionPanelData {
  id: string
  name: string
  focus: string | null
  schemaType: SubsectionSchemaType | null
  schemaLabel: string | null
  synopsis: string | null
  processingTimeMs: number | null
  analysis: ParsedSubsection | null
  source: SubsectionAnalysis
}
