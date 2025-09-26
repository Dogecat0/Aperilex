import { useQuery } from '@tanstack/react-query'
import { aperilexApi, type CompanyAnalysesFilters, type CompanyFilingsFilters } from '@/api'

export interface UseCompanyOptions {
  includeRecentAnalyses?: boolean
  enabled?: boolean
}

export const useCompany = (ticker: string, options: UseCompanyOptions = {}) => {
  const { includeRecentAnalyses = false, enabled = true } = options

  return useQuery({
    queryKey: ['company', ticker, { includeRecentAnalyses }],
    queryFn: () => aperilexApi.companies.getCompany(ticker, includeRecentAnalyses),
    enabled: enabled && !!ticker,
  })
}

export interface UseCompanyAnalysesOptions extends CompanyAnalysesFilters {
  enabled?: boolean
}

export const useCompanyAnalyses = (ticker: string, options: UseCompanyAnalysesOptions = {}) => {
  const { enabled = true, ...filters } = options

  return useQuery({
    queryKey: ['company', ticker, 'analyses', filters],
    queryFn: () => aperilexApi.companies.getCompanyAnalyses(ticker, filters),
    enabled: enabled && !!ticker,
  })
}

export interface UseCompanyFilingsOptions extends CompanyFilingsFilters {
  enabled?: boolean
}

export const useCompanyFilings = (ticker: string, options: UseCompanyFilingsOptions = {}) => {
  const { enabled = true, ...filters } = options

  return useQuery({
    queryKey: ['company', ticker, 'filings', filters],
    queryFn: () => aperilexApi.companies.getCompanyFilings(ticker, filters),
    enabled: enabled && !!ticker,
  })
}
