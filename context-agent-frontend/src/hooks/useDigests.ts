import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Digest } from '../api/types'

export function useDigests() {
  const { user } = useAuth()
  const isAuthenticated = Boolean(user)

  const { data = [], isLoading, isError, error, refetch } = useQuery<Digest[]>({
    queryKey: ['digests'],
    queryFn: () => api.listDigests(),
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
