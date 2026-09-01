import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Sparkles, Newspaper, MessageSquare } from 'lucide-react'
import { api } from '../api/client'
import type { SearchHit } from '../api/types'
import { SearchResults } from '../components/search/SearchResults'
import { TrendingMiniBox } from '../components/home/TrendingMiniBox'
import { SpotlightBriefCard } from '../components/home/SpotlightBriefCard'
import { CategoryHighlights } from '../components/home/CategoryHighlights'

export function HomePage() {
  const [searchParams] = useSearchParams()
  const searchQuery = searchParams.get('q') ?? ''

  const [searchResults, setSearchResults] = useState<SearchHit[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Fetch search matches if a global query is passed in URL
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
      {/* 1. Header & Quick Navigation Bar */}
      <section className="hero" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1>News with Context</h1>
            <p className="muted">
              Live multi-source news intelligence, automated daily topic briefs, and AI retrieval.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <Link to="/articles" className="btn btn-ghost btn-sm">
              <Newspaper size={15} /> All Articles
            </Link>
            <Link to="/briefs" className="btn btn-ghost btn-sm">
              <Sparkles size={15} /> All Briefs
            </Link>
            <Link to="/chat" className="btn btn-primary btn-sm">
              <MessageSquare size={15} /> Ask AI Context
            </Link>
          </div>
        </div>
      </section>

      {/* 2. Content View (Search vs 3-Column Dashboard) */}
      {searchQuery ? (
        <SearchResults
          query={searchQuery}
          results={searchResults}
          loading={searchLoading}
          error={searchError}
        />
      ) : (
        <div className="home-3col-grid">
          {/* Column 1: Top 5 Trending */}
          <TrendingMiniBox />

          {/* Column 2: 1 Spotlight Brief */}
          <SpotlightBriefCard />

          {/* Column 3: Category News Highlights */}
          <CategoryHighlights />
        </div>
      )}
    </div>
  )
}
