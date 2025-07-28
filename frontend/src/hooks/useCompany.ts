import { useQuery } from '@tanstack/react-query'
import { aperilexApi } from '@/api'

export const useCompany = (ticker: string, enabled = true) => {
  return useQuery({
    queryKey: ['company', ticker],
    queryFn: () => aperilexApi.companies.getCompany(ticker),
    enabled: enabled && !!ticker,
  })
}

export const useCompanyAnalyses = (ticker: string, enabled = true) => {
  return useQuery({
    queryKey: ['company', ticker, 'analyses'],
    queryFn: () => aperilexApi.companies.getCompanyAnalyses(ticker),
    enabled: enabled && !!ticker,
  })
}
