import type { SearchHit } from '../../api/types'
import { truncate } from '../../lib/format'

interface SearchResultsProps {
  query: string
  results: SearchHit[]
  loading: boolean
  error?: string
}

export function SearchResults({ query, results, loading, error }: SearchResultsProps) {
  if (!query) return null

  return (
    <section className="search-results">
      <div className="section-header">
        <h2>Search results</h2>
        <span className="muted">“{query}”</span>
      </div>
      {loading && <div className="empty-state">Searching…</div>}
      {error && <div className="empty-state error-text">{error}</div>}
      {!loading && !error && !results.length && (
        <div className="empty-state">No matching excerpts found.</div>
      )}
      <div className="search-hit-list">
        {results.map((hit) => (
          <a key={`${hit.article_id}-${hit.url}`} className="search-hit" href={hit.url} target="_blank" rel="noreferrer">
            <div className="search-hit-meta">
              <span className="badge">{hit.source}</span>
              {hit.categories.slice(0, 2).map((cat) => (
                <span key={cat} className="badge badge-soft">
                  {cat}
                </span>
              ))}
            </div>
            <h3>{hit.title}</h3>
            <p>{truncate(hit.chunk, 220)}</p>
          </a>
        ))}
      </div>
    </section>
  )
}
