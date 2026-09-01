import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { api, API_BASE } from '../api/client'
import type { Category, SearchHit } from '../api/types'
import { ArticleGrid } from '../components/articles/ArticleGrid'
import { CategoryPills } from '../components/articles/CategoryPills'
import { SearchResults } from '../components/search/SearchResults'

export function ArticlesPage() {
  const [searchParams] = useSearchParams()
  const searchQuery = searchParams.get('q') ?? ''
  const queryClient = useQueryClient()

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<SearchHit[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Connection status for real-time WebSocket updates
  const [wsConnected, setWsConnected] = useState(false)
  const observerTarget = useRef<HTMLDivElement | null>(null)

  // Fetch Category pills using React Query (cached)
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => api.listCategories(),
  })

  // Fetch Infinite Articles using React Query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: loading,
  } = useInfiniteQuery({
    queryKey: ['articles', selectedCategory],
    queryFn: ({ pageParam = 1 }) =>
      api.listArticles(pageParam as number, 12, selectedCategory || undefined),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      const currentFetched = allPages.reduce((acc, page) => acc + page.articles.length, 0)
      if (currentFetched >= lastPage.metadata.total || lastPage.articles.length < 12) {
        return undefined
      }
      return allPages.length + 1
    },
    refetchInterval: wsConnected ? false : 30000,
  })

  const articles = data ? data.pages.flatMap((page) => page.articles) : []

  // Throttled query invalidator
  const invalidateRef = useRef<() => void>(undefined)
  if (!invalidateRef.current) {
    let lastCall = 0
    const cooldown = 5000
    invalidateRef.current = () => {
      const now = Date.now()
      if (now - lastCall >= cooldown) {
        lastCall = now
        queryClient.invalidateQueries({ queryKey: ['articles'] })
      }
    }
  }

  // Connect to real-time WebSockets
  useEffect(() => {
    const getWsUrl = () => {
      let base = API_BASE
      if (base.startsWith('/')) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.host
        return `${protocol}//${host}${base}/ws/news`
      }
      return base.replace(/^http/, 'ws') + '/ws/news'
    }

    let socket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let isCancelled = false

    const connect = () => {
      if (isCancelled) return
      const url = getWsUrl()
      socket = new WebSocket(url)

      socket.onopen = () => {
        if (!isCancelled) setWsConnected(true)
      }

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === 'news_updated') {
            invalidateRef.current?.()
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      socket.onclose = () => {
        if (!isCancelled) {
          setWsConnected(false)
          reconnectTimer = window.setTimeout(connect, 5000)
        }
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      isCancelled = true
      if (socket) socket.close()
      if (reconnectTimer) clearTimeout(reconnectTimer)
    }
  }, [queryClient])

  // Setup infinite scroll observer sentinel
  useEffect(() => {
    if (loading || !hasNextPage) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) {
          fetchNextPage()
        }
      },
      { threshold: 0.1 }
    )

    const currentTarget = observerTarget.current
    if (currentTarget) {
      observer.observe(currentTarget)
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget)
      }
    }
  }, [loading, hasNextPage, isFetchingNextPage, fetchNextPage, selectedCategory])

  // Fetch search matches
  useEffect(() => {
    if (!searchQuery) {
      setSearchResults([])
      setSearchError('')
      return
    }
    let cancelled = false
    ;(async () => {
      setSearchLoading(true)
      setSearchError('')
      try {
        const res = await api.bm25Search(searchQuery, 12)
        if (!cancelled) setSearchResults(res.results)
      } catch (err) {
        if (!cancelled) {
          setSearchResults([])
          setSearchError(err instanceof Error ? err.message : 'Search failed')
        }
      } finally {
        if (!cancelled) setSearchLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [searchQuery])

  return (
    <div className="page articles-page">
      <section className="hero" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1>All News Articles</h1>
            <p className="muted">
              Explore the complete multi-source RSS news corpus with real-time live ingestion.
            </p>
          </div>
        </div>
      </section>

      {searchQuery ? (
        <SearchResults
          query={searchQuery}
          results={searchResults}
          loading={searchLoading}
          error={searchError}
        />
      ) : (
        <>
          <CategoryPills
            categories={categories}
            selected={selectedCategory}
            onSelect={setSelectedCategory}
          />
          {loading ? (
            <div className="empty-state">Loading articles…</div>
          ) : (
            <>
              <ArticleGrid
                articles={articles}
                emptyMessage={
                  selectedCategory
                    ? `No articles in “${selectedCategory}” right now.`
                    : 'No articles available yet.'
                }
              />
              {(hasNextPage || isFetchingNextPage) && (
                <div
                  ref={observerTarget}
                  style={{
                    textAlign: 'center',
                    padding: '20px 0',
                    color: 'var(--color-muted)',
                    fontSize: '0.9rem',
                    fontStyle: 'italic',
                  }}
                >
                  {isFetchingNextPage ? 'Loading more articles…' : 'Scroll down to load more'}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
