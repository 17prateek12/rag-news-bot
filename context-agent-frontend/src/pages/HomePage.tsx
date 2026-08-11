import { useEffect, useState } from 'react'
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

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const res = await api.listArticles(1, 'all', selectedCategory || undefined)
        if (!cancelled) setArticles(res.articles)
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
            <ArticleGrid
              articles={articles}
              emptyMessage={
                selectedCategory
                  ? `No articles in “${selectedCategory}” right now.`
                  : 'No articles available yet.'
              }
            />
          )}
        </>
      )}
    </div>
  )
}
