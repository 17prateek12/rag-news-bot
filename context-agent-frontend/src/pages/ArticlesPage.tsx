import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { SearchHit } from '../api/types'
import { ArticleGrid } from '../components/articles/ArticleGrid'
import { CategoryPills } from '../components/articles/CategoryPills'
import { SearchResults } from '../components/search/SearchResults'

export function ArticlesPage() {
  const [searchParams] = useSearchParams()
  const categoryParam = searchParams.get('category')
  const searchQuery = searchParams.get('q') ?? ''

  const [selectedCategory, setSelectedCategory] = useState<string | null>(categoryParam)
  const [searchResults, setSearchResults] = useState<SearchHit[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  const observerTarget = useRef<HTMLDivElement>(null)

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.listCategories(),
  })

  const {
    data,
    isLoading: loading,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useInfiniteQuery({
    queryKey: ['articles', selectedCategory],
    queryFn: ({ pageParam = 1 }) => api.listArticles(pageParam, 12, selectedCategory || undefined),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      return lastPage.articles.length === 12 ? allPages.length + 1 : undefined
    },
  })

  const articles = data ? data.pages.flatMap((page) => page.articles) : []

  // Sync state if URL query param changes
  useEffect(() => {
    setSelectedCategory(categoryParam)
  }, [categoryParam])

  // Real-time WebSocket connection
  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimeout: number | undefined
    let isMounted = true

    const connect = () => {
      if (!isMounted) return

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.host
      const wsUrl = `${wsProtocol}//${wsHost}/ws/news`

      try {
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          // Connected
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'new_articles') {
              // Real-time update
            }
          } catch {
            // Ignore parse error
          }
        }

        ws.onerror = () => {
          // Handled in onclose
        }

        ws.onclose = (event) => {
          // Clean close or auth rejected (4001: unauthorized)
          if (event.code === 4001) {
            return
          }
          if (isMounted) {
            reconnectTimeout = window.setTimeout(connect, 5000)
          }
        }
      } catch {
        if (isMounted) {
          reconnectTimeout = window.setTimeout(connect, 5000)
        }
      }
    }

    connect()

    return () => {
      isMounted = false
      clearTimeout(reconnectTimeout)
      if (ws) {
        ws.close()
      }
    }
  }, [])

  // Infinite scroll observer sentinel
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
      <section className="hero">
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
