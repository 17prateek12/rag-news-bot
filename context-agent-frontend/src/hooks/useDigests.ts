import { useQuery } from '@tanstack/react-query'
import { api, getToken } from '../api/client'
import type { Digest } from '../api/types'

export function useDigests(days: number = 7) {
  const hasAuthToken = Boolean(getToken())

  const { data = [], isLoading, isError, error, refetch } = useQuery<Digest[]>({
    queryKey: ['digests', days],
    queryFn: () => api.listDigests(days),
    enabled: hasAuthToken,
    staleTime: 60000 * 5, // 5 minutes
  })

  const spotlightDigest: Digest | null = data.length > 0 ? data[0] : null

  return {
    digests: data,
    spotlightDigest,
    hasBriefs: data.length > 0,
    isAuthenticated: hasAuthToken,
    isLoading: hasAuthToken ? isLoading : false,
    isError,
    error,
    refetch,
  }
}
