import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Digest } from '../api/types'

export function useDigests(days: number = 7) {
  const { user } = useAuth()
  const isAuthenticated = Boolean(user)

  const { data = [], isLoading, isError, error, refetch } = useQuery<Digest[]>({
    queryKey: ['digests', days],
    queryFn: () => api.listDigests(days),
    enabled: isAuthenticated,
    staleTime: 60000 * 5, // 5 minutes
  })

  const spotlightDigest: Digest | null = data.length > 0 ? data[0] : null

  return {
    digests: data,
    spotlightDigest,
    hasBriefs: data.length > 0,
    isAuthenticated,
    isLoading: isAuthenticated ? isLoading : false,
    isError,
    error,
    refetch,
  }
}
