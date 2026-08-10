import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { SearchHit, TrendingQuery } from '../api/types'
import { dedupeSearchHits, filterTrendingQueries } from '../lib/trendingFilters'

export function TrendingPage() {
  const [topics, setTopics] = useState<TrendingQuery[]>([])
  const [selected, setSelected] = useState<TrendingQuery | null>(null)
  const [searchHits, setSearchHits] = useState<SearchHit[]>([])
  const [loadingTopics, setLoadingTopics] = useState(true)
  const [loadingArticles, setLoadingArticles] = useState(false)

  useEffect(() => {
    ;(async () => {
      setLoadingTopics(true)
      try {
        const res = await api.getTrending(20)
        const filtered = filterTrendingQueries(res.queries)
        setTopics(filtered)
        setSelected(filtered[0] ?? null)
      } finally {
        setLoadingTopics(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!selected) return
    let cancelled = false
    ;(async () => {
      setLoadingArticles(true)
      try {
        const search = await api.hybridSearch(selected.query, 12, true)
        if (cancelled) return
        setSearchHits(dedupeSearchHits(search.results))
      } catch {
        if (!cancelled) setSearchHits([])
      } finally {
        if (!cancelled) setLoadingArticles(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selected])

  return (
    <div className="page trending-page">
      <div className="section-header">
        <h1>Trending</h1>
        <span className="muted">Popular topics in the last 24 hours</span>
      </div>
      <div className="trending-layout">
        <aside className="trending-topics">
          {loadingTopics && <div className="empty-state">Loading topics…</div>}
          {!loadingTopics && !topics.length && (
            <div className="empty-state">No trending topics yet. Ask the agent something!</div>
          )}
          {topics.map((topic, index) => (
            <button
              key={topic.query}
              type="button"
              className={`trending-topic${selected?.query === topic.query ? ' active' : ''}`}
              onClick={() => setSelected(topic)}
            >
              <span className="trending-rank">{index + 1}</span>
              <span className="trending-topic-text">{topic.topic}</span>
              <span className="trending-count">{topic.count}</span>
            </button>
          ))}
        </aside>
        <section className="trending-articles">
          {selected && (
            <div className="section-header compact">
              <h2>Related coverage</h2>
              <span className="muted">{selected.topic}</span>
            </div>
          )}
          {loadingArticles ? (
            <div className="empty-state">Loading articles…</div>
          ) : searchHits.length ? (
            <div className="search-hit-list">
              {searchHits.map((hit) => (
                <a
                  key={`${hit.article_id}-${hit.url}`}
                  className="search-hit"
                  href={hit.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className="search-hit-meta">
                    <span className="badge">{hit.source}</span>
                    {hit.categories.slice(0, 2).map((cat) => (
                      <span key={cat} className="badge badge-soft">
                        {cat}
                      </span>
                    ))}
                  </div>
                  <h3>{hit.title}</h3>
                  <p>{hit.chunk}</p>
                </a>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              {selected
                ? `No related articles found for “${selected.topic}”.`
                : 'Select a trending topic to see related articles.'}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
