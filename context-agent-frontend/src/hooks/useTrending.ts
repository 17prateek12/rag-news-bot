import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { TrendingEntityResponse, TrendingResponse } from '../api/types'

export function useTrending(limit: number = 5) {
  const { data, isLoading, isError, error, refetch } = useQuery<TrendingResponse>({
    queryKey: ['trending', limit],
    queryFn: () => api.getTrending(limit),
    staleTime: 60000, // 1 minute
  })

  const trendingNews: TrendingEntityResponse[] = data?.trending_news ?? []
  const trendingSearches: TrendingEntityResponse[] = data?.trending_searches ?? []

  return {
    trendingNews,
    trendingSearches,
    window: data?.window ?? '24h',
    isLoading,
    isError,
    error,
    refetch,
  }
}
