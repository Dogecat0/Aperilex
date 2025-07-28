import { useQuery } from '@tanstack/react-query'
import { aperilexApi } from '@/api'

export const useFiling = (accessionNumber: string, enabled = true) => {
  return useQuery({
    queryKey: ['filing', accessionNumber],
    queryFn: () => aperilexApi.filings.getFiling(accessionNumber),
    enabled: enabled && !!accessionNumber,
  })
}

export const useFilingAnalysis = (accessionNumber: string, enabled = true) => {
  return useQuery({
    queryKey: ['filing', accessionNumber, 'analysis'],
    queryFn: () => aperilexApi.filings.getFilingAnalysis(accessionNumber),
    enabled: enabled && !!accessionNumber,
  })
}
