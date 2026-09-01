import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Article, PaginatedArticlesResponse } from '../api/types'

export function useCategoryHighlights(limit: number = 4) {
  const { data, isLoading, isError, error } = useQuery<PaginatedArticlesResponse>({
    queryKey: ['category-highlights', limit],
    queryFn: () => api.listArticles(1, limit),
    staleTime: 60000 * 2, // 2 minutes
  })

  const articles: Article[] = data?.articles ?? []
  const totalCount: number = data?.metadata.total ?? 0

  return {
    articles,
    totalCount,
    isLoading,
    isError,
    error,
  }
}
