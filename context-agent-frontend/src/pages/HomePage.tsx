import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Article, Category, SearchHit } from '../api/types'
import { ArticleGrid } from '../components/articles/ArticleGrid'
import { CategoryPills } from '../components/articles/CategoryPills'
import { SearchResults } from '../components/search/SearchResults'

export function HomePage() {
  const [searchParams] = useSearchParams()
  const searchQuery = searchParams.get('q') ?? ''

  const [categories, setCategories] = useState<Category[]>([])
  const [articles, setArticles] = useState<Article[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchResults, setSearchResults] = useState<SearchHit[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Infinite Scroll States
  const [pageNo, setPageNo] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const observerTarget = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const cats = await api.listCategories()
        if (!cancelled) setCategories(cats)
      } catch (err) {
        console.error('Failed to list categories', err)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Initial load for a category selection
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setPageNo(1)
      setHasMore(true)
      try {
        const res = await api.listArticles(1, 12, selectedCategory || undefined)
        if (!cancelled) {
          setArticles(res.articles)
          if (res.articles.length < 12 || res.articles.length >= res.metadata.total) {
            setHasMore(false)
          }
        }
      } catch {
        if (!cancelled) setArticles([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedCategory])

  const fetchNextPage = async () => {
    if (loading || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const nextPage = pageNo + 1
      const res = await api.listArticles(nextPage, 12, selectedCategory || undefined)
      setArticles(prev => {
        const combined = [...prev, ...res.articles]
        if (combined.length >= res.metadata.total || res.articles.length < 12) {
          setHasMore(false)
        }
        return combined
      })
      setPageNo(nextPage)
    } catch (err) {
      console.error('Failed to load more articles', err)
    } finally {
      setLoadingMore(false)
    }
  }

  // Set up IntersectionObserver sentinel
  useEffect(() => {
    if (loading || !hasMore) return

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting) {
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
  }, [loading, hasMore, pageNo, selectedCategory, loadingMore])

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
    <div className="page home-page">
      <section className="hero">
        <h1>News with context</h1>
        <p className="muted">
          Browse curated RSS feeds, explore trending topics, or chat with the agent for deeper
          background on what matters.
        </p>
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
              {hasMore && (
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
                  {loadingMore ? 'Loading more articles…' : 'Scroll down to load more'}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
